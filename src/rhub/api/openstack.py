import logging

from connexion import problem
from flask import url_for
from werkzeug.exceptions import Forbidden

from rhub.api import DEFAULT_PAGE_LIMIT, db
from rhub.api.utils import db_sort
from rhub.api.vault import Vault
from rhub.auth import ADMIN_ROLE
from rhub.auth.keycloak import KeycloakClient, KeycloakGetError
from rhub.openstack import model


logger = logging.getLogger(__name__)


VAULT_PATH_PREFIX = 'kv/openstack'
"""Vault path prefix to create new credentials in Vault."""


def _cloud_href(cloud):
    href = {
        'cloud': url_for('.rhub_api_openstack_cloud_get',
                         cloud_id=cloud.id),
        'owner_group': url_for('.rhub_api_auth_group_get_group',
                               group_id=cloud.owner_group_id)
    }
    return href


def cloud_list(filter_, sort=None, page=0, limit=DEFAULT_PAGE_LIMIT):
    clouds = model.Cloud.query

    if 'name' in filter_:
        clouds = clouds.filter(model.Cloud.name.ilike(filter_['name']))

    if 'owner_group_id' in filter_:
        clouds = clouds.filter(model.Cloud.owner_group_id == filter_['owner_group_id'])

    if sort:
        clouds = db_sort(clouds, sort)

    return {
        'data': [
            cloud.to_dict() | {'_href': _cloud_href(cloud)}
            for cloud in clouds.limit(limit).offset(page * limit)
        ],
        'total': clouds.count(),
    }


def cloud_create(keycloak: KeycloakClient, vault: Vault, body, user):
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

    query = model.Cloud.query.filter(model.Cloud.name == body['name'])
    if query.count() > 0:
        return problem(
            400, 'Bad Request',
            f'Cloud with name {body["name"]!r} already exists',
        )

    credentials = body['credentials']
    if not isinstance(credentials, str):
        credentials_path = f'{VAULT_PATH_PREFIX}/{body["name"]}'
        vault.write(credentials_path, credentials)
        body['credentials'] = credentials_path

    cloud = model.Cloud.from_dict(body)

    db.session.add(cloud)
    db.session.commit()
    logger.info(f'Cloud {cloud.name} (id {cloud.id}) created by user {user}')

    return cloud.to_dict() | {'_href': _cloud_href(cloud)}


def cloud_get(cloud_id):
    cloud = model.Cloud.query.get(cloud_id)
    if not cloud:
        return problem(404, 'Not Found', f'Cloud {cloud_id} does not exist')
    return cloud.to_dict() | {'_href': _cloud_href(cloud)}


def cloud_update(keycloak: KeycloakClient, vault: Vault, cloud_id, body, user):
    cloud = model.Cloud.query.get(cloud_id)
    if not cloud:
        return problem(404, 'Not Found', f'Cloud {cloud_id} does not exist')

    if not keycloak.user_check_role(user, ADMIN_ROLE):
        if not keycloak.user_check_group(user, cloud.owner_group_id):
            raise Forbidden('You are not owner of this cloud.')

    credentials = body.get('credentials', cloud.credentials)
    if not isinstance(credentials, str):
        vault.write(cloud.credentials, credentials)
        del body['credentials']

    cloud.update_from_dict(body)

    db.session.commit()
    logger.info(f'Cloud {cloud.name} (id {cloud.id}) updated by user {user}')

    return cloud.to_dict() | {'_href': _cloud_href(cloud)}


def cloud_delete(keycloak: KeycloakClient, cloud_id, user):
    cloud = model.Cloud.query.get(cloud_id)
    if not cloud:
        return problem(404, 'Not Found', f'Cloud {cloud_id} does not exist')

    if not keycloak.user_check_role(user, ADMIN_ROLE):
        if not keycloak.user_check_group(user, cloud.owner_group_id):
            raise Forbidden('You are not owner of this cloud.')

    db.session.delete(cloud)
    db.session.commit()
    logger.info(f'Cloud {cloud.name} (id {cloud.id}) deleted by user {user}')
