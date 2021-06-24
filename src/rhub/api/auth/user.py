import logging

from flask import request
from connexion import problem
from keycloak import KeycloakGetError

from rhub.api import get_keycloak
from rhub.auth.keycloak import problem_from_keycloak_error
from rhub.auth.utils import route_require_admin


logger = logging.getLogger(__name__)


def list_users():
    try:
        return get_keycloak().user_list({}), 200
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


@route_require_admin
def create_user(body, user):
    try:
        user_id = get_keycloak().user_create(body)
        logger.info(f'Created user {user_id}')
        return get_keycloak().user_get(user_id), 200
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


def get_user(user_id):
    try:
        return get_keycloak().user_get(user_id), 200
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


@route_require_admin
def update_user(user_id, body, user):
    try:
        get_keycloak().user_update(user_id, body)
        logger.info(f'Updated user {user_id}')
        return get_keycloak().user_get(user_id), 200
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


@route_require_admin
def delete_user(user_id, user):
    try:
        get_keycloak().user_delete(user_id)
        logger.info(f'Deleted user {user_id}')
        return {}, 200
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


def list_user_groups(user_id):
    try:
        return get_keycloak().user_group_list(user_id), 200
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


@route_require_admin
def add_user_group(user_id, body, user):
    try:
        get_keycloak().group_user_add(user_id, body['id'])
        return {}, 200
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


@route_require_admin
def delete_user_group(user_id, user):
    try:
        get_keycloak().group_user_remove(user_id, request.json['id'])
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


def get_current_user(user):
    try:
        return get_keycloak().user_get(user), 200
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))
