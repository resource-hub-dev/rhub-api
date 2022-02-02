import logging

from connexion import problem
from flask import url_for

from rhub.auth.keycloak import (
    KeycloakClient, KeycloakGetError, problem_from_keycloak_error,
)
from rhub.auth.utils import route_require_admin


logger = logging.getLogger(__name__)


def _role_href(role):
    return {
        'role': url_for('.rhub_api_auth_role_get_role',
                        role_id=role['id']),
    }


# These are "realm-level" roles, "client" level roles can be implemented
# separately later if needed.

def list_roles(keycloak: KeycloakClient):
    try:
        return [
            role | {'_href': _role_href(role)}
            for role in keycloak.role_list()
        ]
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


@route_require_admin
def create_role(keycloak: KeycloakClient, body, user):
    try:
        role_id = keycloak.role_create(body)
        logger.info(f'Create role {role_id}')
        role_data = keycloak.role_get(role_id)
        return role_data | {'_href': _role_href(role_data)}
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


def get_role(keycloak: KeycloakClient, role_id):
    try:
        role_data = keycloak.role_get(role_id)
        return role_data | {'_href': _role_href(role_data)}
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


@route_require_admin
def update_role(keycloak: KeycloakClient, role_id, body, user):
    try:
        keycloak.role_update(role_id, body)
        role_name = body['name']
        logger.info(f'Updated role {role_id}')
        role_data = keycloak.role_get(role_name)
        return role_data | {'_href': _role_href(role_data)}
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


@route_require_admin
def delete_role(keycloak: KeycloakClient, role_id, user):
    try:
        keycloak.role_delete(role_id)
        logger.info(f'Deleted role {role_id}')
        return {}, 200
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))
