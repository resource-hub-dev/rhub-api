import logging

from connexion import problem
from flask import url_for

from rhub.auth.keycloak import (
    KeycloakClient, KeycloakGetError, problem_from_keycloak_error,
)
from rhub.auth.utils import route_require_admin


logger = logging.getLogger(__name__)


def _group_href(group):
    return {
        'group': url_for('.rhub_api_auth_group_get_group',
                         group_id=group['id']),
        'group_roles': url_for('.rhub_api_auth_group_list_group_roles',
                               group_id=group['id']),
        'group_users': url_for('.rhub_api_auth_group_list_group_users',
                               group_id=group['id']),
    }


def list_groups(keycloak: KeycloakClient):
    try:
        return [
            group | {'_href': _group_href(group)}
            for group in keycloak.group_list()
        ]
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


@route_require_admin
def create_group(keycloak: KeycloakClient, body, user):
    try:
        group_id = keycloak.group_create(body)
        logger.info(f'Created group {group_id}')
        group_data = keycloak.group_get(group_id)
        return group_data | {'_href': _group_href(group_data)}
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


def get_group(keycloak: KeycloakClient, group_id):
    try:
        group_data = keycloak.group_get(group_id)
        return group_data | {'_href': _group_href(group_data)}
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


@route_require_admin
def update_group(keycloak: KeycloakClient, group_id, body, user):
    try:
        keycloak.group_update(group_id, body)
        logger.info(f'Updated group {group_id}')
        group_data = keycloak.group_get(group_id)
        return group_data | {'_href': _group_href(group_data)}
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


@route_require_admin
def delete_group(keycloak: KeycloakClient, group_id, user):
    try:
        keycloak.group_delete(group_id)
        logger.info(f'Deleted group {group_id}')
        return {}, 200
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


def list_group_users(keycloak: KeycloakClient, group_id):
    try:
        from rhub.api.auth.user import _user_href
        return [
            user | {'_href': _user_href(user)}
            for user in keycloak.group_user_list(group_id)
        ]
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


def list_group_roles(group_id):
    raise NotImplementedError


@route_require_admin
def add_group_role(group_id, body, user):
    raise NotImplementedError


@route_require_admin
def delete_group_role(group_id, body, user):
    raise NotImplementedError
