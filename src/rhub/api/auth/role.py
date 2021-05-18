import logging

from connexion import problem
from keycloak import KeycloakGetError

from rhub.api import get_keycloak
from rhub.auth.keycloak import problem_from_keycloak_error


logger = logging.getLogger(__name__)


# These are "realm-level" roles, "client" level roles can be implemented
# separately later if needed.

def list_roles():
    try:
        return get_keycloak().role_list(), 200
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


def create_role(body):
    try:
        role_id = get_keycloak().role_create(body)
        logger.info(f'Create role {role_id}')
        return get_keycloak().role_get(role_id), 200
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


def get_role(id):
    try:
        return get_keycloak().role_get(id), 200
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


def update_role(id, body):
    try:
        get_keycloak().role_update(id, body)
        role_name = body['name']
        logger.info(f'Updated role {id}')
        return get_keycloak().role_get(role_name), 200
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


def delete_role(id):
    try:
        get_keycloak().role_delete(id)
        logger.info(f'Deleted role {id}')
        return {}, 200
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))
