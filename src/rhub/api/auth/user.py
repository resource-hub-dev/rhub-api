import logging

from flask import request, url_for
from connexion import problem

from rhub.api import DEFAULT_PAGE_LIMIT
from rhub.auth.keycloak import (
    KeycloakClient, KeycloakGetError, problem_from_keycloak_error,
)
from rhub.auth.utils import route_require_admin


logger = logging.getLogger(__name__)


def _user_href(user):
    return {
        'user': url_for('.rhub_api_auth_user_get_user',
                        user_id=user['id']),
        'user_groups': url_for('.rhub_api_auth_user_list_user_groups',
                               user_id=user['id']),
        'user_roles': url_for('.rhub_api_auth_user_list_user_roles',
                              user_id=user['id']),
    }


def list_users(keycloak: KeycloakClient, filter_, page=0, limit=DEFAULT_PAGE_LIMIT):
    try:
        return [
            user | {'_href': _user_href(user)}
            for user in keycloak.user_list({
                'first': page * limit,
                'max': limit,
                **filter_,
            })
        ]
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


@route_require_admin
def create_user(keycloak: KeycloakClient, body, user):
    try:
        user_id = keycloak.user_create(body)
        logger.info(f'Created user {user_id}')
        user_data = keycloak.user_get(user_id)
        return user_data | {'_href': _user_href(user_data)}
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


def get_user(keycloak: KeycloakClient, user_id):
    try:
        user_data = keycloak.user_get(user_id)
        return user_data | {'_href': _user_href(user_data)}
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


@route_require_admin
def update_user(keycloak: KeycloakClient, user_id, body, user):
    try:
        keycloak.user_update(user_id, body)
        logger.info(f'Updated user {user_id}')
        user_data = keycloak.user_get(user_id)
        return user_data | {'_href': _user_href(user_data)}
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


@route_require_admin
def delete_user(keycloak: KeycloakClient, user_id, user):
    try:
        keycloak.user_delete(user_id)
        logger.info(f'Deleted user {user_id}')
        return {}, 200
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


def list_user_groups(keycloak: KeycloakClient, user_id):
    try:
        from rhub.api.auth.group import _group_href
        return [
            group | {'_href': _group_href(group)}
            for group in keycloak.user_group_list(user_id)
        ]
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


@route_require_admin
def add_user_group(keycloak: KeycloakClient, user_id, body, user):
    try:
        keycloak.group_user_add(user_id, body['id'])
        return {}, 200
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


@route_require_admin
def delete_user_group(keycloak: KeycloakClient, user_id, user):
    try:
        keycloak.group_user_remove(user_id, request.json['id'])
        return {}, 200
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


def list_user_roles(user_id):
    raise NotImplementedError


@route_require_admin
def add_user_role(user_id, body, user):
    raise NotImplementedError


@route_require_admin
def delete_user_role(user_id, body, user):
    raise NotImplementedError


def get_current_user(keycloak: KeycloakClient, user):
    try:
        user_data = keycloak.user_get(user)
        return user_data | {'_href': _user_href(user_data)}
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))
