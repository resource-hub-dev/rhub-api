import logging

from connexion import problem
from keycloak import KeycloakGetError

from rhub.api import get_keycloak
from rhub.auth.keycloak import problem_from_keycloak_error


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


def create_group(body):
    try:
        group_id = get_keycloak().group_create(body)
        logger.info(f'Created group {id}')
        return get_keycloak().group_get(group_id), 200
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


def get_group(id):
    try:
        return get_keycloak().group_get(id), 200
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


def update_group(id, body):
    try:
        get_keycloak().group_update(id, body)
        logger.info(f'Updated group {id}')
        return get_keycloak().group_get(id), 200
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


def delete_group(id):
    try:
        get_keycloak().group_delete(id)
        logger.info(f'Deleted group {id}')
        return {}, 200
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


def list_group_users(id):
    try:
        return get_keycloak().group_user_list(id), 200
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


def list_group_roles(id):
    raise NotImplementedError


def add_group_role(id, body):
    raise NotImplementedError


def delete_group_role(id, body):
    raise NotImplementedError
