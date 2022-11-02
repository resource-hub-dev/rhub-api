import logging

from connexion import problem
from flask import url_for
from werkzeug.exceptions import Forbidden

from rhub.api import DEFAULT_PAGE_LIMIT, db
from rhub.api.utils import db_sort
from rhub.api.vault import Vault
from rhub.auth import ADMIN_ROLE
from rhub.auth.keycloak import KeycloakClient, KeycloakGetError
from rhub.satellite import model


logger = logging.getLogger(__name__)


VAULT_PATH_PREFIX = 'kv/satellite'
"""Vault path prefix to create new credentials in Vault."""


def _server_href(server):
    href = {
        'server': url_for('.rhub_api_satellite_server_get',
                          server_id=server.id),
    }
    return href


def server_list(filter_, sort=None, page=0, limit=DEFAULT_PAGE_LIMIT):
    servers = model.SatelliteServer.query

    if 'name' in filter_:
        servers = servers.filter(model.SatelliteServer.hostname.ilike(filter_['name']))

    if 'owner_group_id' in filter_:
        servers = servers.filter(
            model.SatelliteServer.owner_group_id == filter_['owner_group_id']
        )

    if sort:
        servers = db_sort(servers, sort)

    return {
        'data': [
            server.to_dict() | {'_href': _server_href(server)}
            for server in servers.limit(limit).offset(page * limit)
        ],
        'total': servers.count(),
    }


def server_create(keycloak: KeycloakClient, vault: Vault, body, user):
    try:
        if body.get('owner_group_id'):
            keycloak.group_get(body['owner_group_id'])
    except KeycloakGetError as e:
        logger.exception(e)
        return problem(
            400, 'Owner group does not exist',
            f'Owner group {body["owner_group_id"]} does not exist in Keycloak, '
            'you have to create group first or use existing group.'
        )

    credentials = body.pop('credentials')
    if isinstance(credentials, str):
        body['credentials'] = credentials
    else:
        body['credentials'] = f'{VAULT_PATH_PREFIX}/{body["name"]}'

    server = model.SatelliteServer.from_dict(body)

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
    server = model.SatelliteServer.query.get(server_id)
    if not server:
        return problem(404, 'Not Found', f'Server {server_id} does not exist')
    return server.to_dict() | {'_href': _server_href(server)}


def server_update(keycloak: KeycloakClient, vault: Vault, server_id, body, user):
    server = model.SatelliteServer.query.get(server_id)
    if not server:
        return problem(404, 'Not Found', f'Server {server_id} does not exist')

    if not keycloak.user_check_role(user, ADMIN_ROLE):
        if not keycloak.user_check_group(user, server.owner_group_id):
            raise Forbidden('You are not owner of this server.')

    credentials = body.pop('credentials', None)
    if isinstance(credentials, str):
        server.credentials = credentials

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


def server_delete(keycloak: KeycloakClient, server_id, user):
    server = model.SatelliteServer.query.get(server_id)
    if not server:
        return problem(404, 'Not Found', f'Server {server_id} does not exist')

    if not keycloak.user_check_role(user, ADMIN_ROLE):
        if not keycloak.user_check_group(user, server.owner_group_id):
            raise Forbidden('You are not owner of this server.')

    db.session.delete(server)
    db.session.commit()

    logger.info(
        f'Server {server.name} (id {server.id}) deleted by user {user}',
        extra={'user_id': user, 'server_id': server.id},
    )
