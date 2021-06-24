import logging

from connexion import problem
from keycloak import KeycloakGetError

from rhub.api import get_keycloak
from rhub.auth.keycloak import problem_from_keycloak_error
from rhub.auth.utils import route_require_admin


logger = logging.getLogger(__name__)


def list_groups():
    try:
        return get_keycloak().group_list(), 200
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


@route_require_admin
def create_group(body, user):
    try:
        group_id = get_keycloak().group_create(body)
        logger.info(f'Created group {group_id}')
        return get_keycloak().group_get(group_id), 200
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


def get_group(group_id):
    try:
        return get_keycloak().group_get(group_id), 200
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


@route_require_admin
def update_group(group_id, body, user):
    try:
        get_keycloak().group_update(group_id, body)
        logger.info(f'Updated group {group_id}')
        return get_keycloak().group_get(group_id), 200
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


@route_require_admin
def delete_group(group_id, user):
    try:
        get_keycloak().group_delete(group_id)
        logger.info(f'Deleted group {group_id}')
        return {}, 200
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


def list_group_users(group_id):
    try:
        return get_keycloak().group_user_list(group_id), 200
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
