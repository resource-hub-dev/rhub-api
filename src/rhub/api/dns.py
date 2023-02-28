import logging

from connexion import problem
from flask import url_for
from werkzeug.exceptions import Forbidden

from rhub import auth
from rhub.api import DEFAULT_PAGE_LIMIT, db
from rhub.api.utils import db_sort
from rhub.api.vault import Vault
from rhub.auth import model as auth_model
from rhub.dns import model


logger = logging.getLogger(__name__)


VAULT_PATH_PREFIX = 'kv/dns'
"""Vault path prefix to create new credentials in Vault."""


def _server_href(server):
    href = {
        'server': url_for('.rhub_api_dns_server_get',
                          server_id=server.id),
        'owner_group': url_for('.rhub_api_auth_group_group_get',
                               group_id=server.owner_group_id),
    }
    return href


def server_list(filter_, sort=None, page=0, limit=DEFAULT_PAGE_LIMIT):
    servers = model.DnsServer.query

    if 'name' in filter_:
        servers = servers.filter(model.DnsServer.hostname.ilike(filter_['name']))

    if 'owner_group_id' in filter_:
        servers = servers.filter(model.DnsServer.owner_group_id == filter_['owner_group_id'])

    if 'owner_group_name' in filter_:
        servers = servers.outerjoin(
            auth_model.Group,
            auth_model.Group.id == model.DnsServer.owner_group_id,
        )
        servers = servers.filter(auth_model.Group.name == filter_['owner_group_name'])

    if sort:
        servers = db_sort(servers, sort)

    return {
        'data': [
            server.to_dict() | {'_href': _server_href(server)}
            for server in servers.limit(limit).offset(page * limit)
        ],
        'total': servers.count(),
    }


def server_create(vault: Vault, body, user):
    credentials = body.pop('credentials')
    if isinstance(credentials, str):
        body['credentials'] = credentials
    else:
        body['credentials'] = f'{VAULT_PATH_PREFIX}/{body["name"]}'

    vault.check_write(body['credentials'])

    server = model.DnsServer.from_dict(body)

    db.session.add(server)
    db.session.flush()

    if isinstance(credentials, dict):
        vault.write(server.credentials, credentials)

    db.session.commit()

    logger.info(
        f'Server {server.name} (id {server.id}) created by user {user}',
        extra={'user_id': user, 'server_id': server.id},
    )

    return server.to_dict() | {'_href': _server_href(server)}


def server_get(server_id):
    server = model.DnsServer.query.get(server_id)
    if not server:
        return problem(404, 'Not Found', f'Server {server_id} does not exist')
    return server.to_dict() | {'_href': _server_href(server)}


def server_update(vault: Vault, server_id, body, user):
    server = model.DnsServer.query.get(server_id)
    if not server:
        return problem(404, 'Not Found', f'Server {server_id} does not exist')

    if not auth.utils.user_is_admin(user):
        if server.owner_group_id not in auth.utils.user_group_ids(user):
            raise Forbidden('You are not owner of this server.')

    credentials = body.pop('credentials', None)
    if isinstance(credentials, str):
        server.credentials = credentials

    vault.check_write(server.credentials)

    server.update_from_dict(body)
    db.session.flush()

    if isinstance(credentials, dict):
        vault.write(server.credentials, credentials)

    db.session.commit()

    logger.info(
        f'Server {server.name} (id {server.id}) updated by user {user}',
        extra={'user_id': user, 'server_id': server.id},
    )

    return server.to_dict() | {'_href': _server_href(server)}


def server_delete(server_id, user):
    server = model.DnsServer.query.get(server_id)
    if not server:
        return problem(404, 'Not Found', f'Server {server_id} does not exist')

    if not auth.utils.user_is_admin(user):
        if server.owner_group_id not in auth.utils.user_group_ids(user):
            raise Forbidden('You are not owner of this server.')

    db.session.delete(server)
    db.session.commit()

    logger.info(
        f'Server {server.name} (id {server.id}) deleted by user {user}',
        extra={'user_id': user, 'server_id': server.id},
    )
