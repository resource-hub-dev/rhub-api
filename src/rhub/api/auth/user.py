import logging

from flask import request
from connexion import problem
from keycloak import KeycloakGetError

from rhub.api import get_keycloak
from rhub.auth.keycloak import problem_from_keycloak_error


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


def create_user(body):
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


def get_user(id):
    try:
        return get_keycloak().user_get(id), 200
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


def update_user(id, body):
    try:
        get_keycloak().user_update(id, body)
        logger.info(f'Updated user {id}')
        return get_keycloak().user_get(id), 200
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


def delete_user(id):
    try:
        get_keycloak().user_delete(id)
        logger.info(f'Deleted user {id}')
        return {}, 200
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


def list_user_groups(id):
    try:
        return get_keycloak().user_group_list(id), 200
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


def add_user_group(id, body):
    try:
        get_keycloak().group_user_add(id, body['id'])
        return {}, 200
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


def delete_user_group(id):
    try:
        get_keycloak().group_user_remove(id, request.json['id'])
        return {}, 200
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


def list_user_roles(id):
    raise NotImplementedError


def add_user_role(id, body):
    raise NotImplementedError


def delete_user_role(id, body):
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
