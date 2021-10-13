import logging

from connexion import problem

from rhub.auth.keycloak import (
    KeycloakClient, KeycloakGetError, problem_from_keycloak_error,
)
from rhub.auth.utils import route_require_admin


logger = logging.getLogger(__name__)


def list_groups(keycloak: KeycloakClient):
    try:
        return keycloak.group_list(), 200
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
        return keycloak.group_get(group_id), 200
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


def get_group(keycloak: KeycloakClient, group_id):
    try:
        return keycloak.group_get(group_id), 200
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
        return keycloak.group_get(group_id), 200
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
        return keycloak.group_user_list(group_id), 200
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
