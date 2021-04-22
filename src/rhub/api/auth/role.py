import logging

from flask import Response
from keycloak import KeycloakGetError

from rhub.api import get_keycloak


logger = logging.getLogger(__name__)


# These are "realm-level" roles, "client" level roles can be implemented
# separately later if needed.

def list_roles():
    try:
        return get_keycloak().role_list(), 200
    except KeycloakGetError as e:
        logger.exception(e)
        return Response(e.response_body, e.response_code)
    except Exception as e:
        logger.exception(e)
        return {'error': str(e)}, 400


def create_role(body):
    try:
        role_id = get_keycloak().role_create(body)
        logger.info(f'Create role {role_id}')
        return get_keycloak().role_get(role_id), 200
    except KeycloakGetError as e:
        logger.exception(e)
        return Response(e.response_body, e.response_code)
    except Exception as e:
        logger.exception(e)
        return {'error': str(e)}, 400


def get_role(id):
    try:
        return get_keycloak().role_get(id), 200
    except KeycloakGetError as e:
        logger.exception(e)
        return Response(e.response_body, e.response_code)
    except Exception as e:
        logger.exception(e)
        return {'error': str(e)}, 400


def update_role(id, body):
    try:
        get_keycloak().role_update(id, body)
        role_name = body['name']
        logger.info(f'Updated role {id}')
        return get_keycloak().role_get(role_name), 200
    except KeycloakGetError as e:
        logger.exception(e)
        return Response(e.response_body, e.response_code)
    except Exception as e:
        logger.exception(e)
        return {'error': str(e)}, 400


def delete_role(id):
    try:
        get_keycloak().role_delete(id)
        logger.info(f'Deleted role {id}')
        return {}, 200
    except KeycloakGetError as e:
        logger.exception(e)
        return Response(e.response_body, e.response_code)
    except Exception as e:
        logger.exception(e)
        return {'error': str(e)}, 400
