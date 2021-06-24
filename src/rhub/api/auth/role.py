import logging

from connexion import problem
from keycloak import KeycloakGetError

from rhub.api import get_keycloak
from rhub.auth.keycloak import problem_from_keycloak_error
from rhub.auth.utils import route_require_admin


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


@route_require_admin
def create_role(body, user):
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


def get_role(role_id):
    try:
        return get_keycloak().role_get(role_id), 200
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


@route_require_admin
def update_role(role_id, body, user):
    try:
        get_keycloak().role_update(role_id, body)
        role_name = body['name']
        logger.info(f'Updated role {role_id}')
        return get_keycloak().role_get(role_name), 200
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


@route_require_admin
def delete_role(role_id, user):
    try:
        get_keycloak().role_delete(role_id)
        logger.info(f'Deleted role {role_id}')
        return {}, 200
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))
