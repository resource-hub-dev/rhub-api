import logging

from flask import g, Response
from keycloak import KeycloakGetError


logger = logging.getLogger(__name__)


def list_groups():
    try:
        return g.keycloak.group_list(), 200
    except KeycloakGetError as e:
        logger.exception(e)
        return Response(e.response_body, e.response_code)
    except Exception as e:
        logger.exception(e)
        return {'error': str(e)}, 400


def create_group(body):
    try:
        group_id = g.keycloak.group_create(body)
        logger.info(f'Created group {id}')
        return g.keycloak.group_get(group_id), 200
    except KeycloakGetError as e:
        logger.exception(e)
        return Response(e.response_body, e.response_code)
    except Exception as e:
        logger.exception(e)
        return {'error': str(e)}, 400


def get_group(id):
    try:
        return g.keycloak.group_get(id), 200
    except KeycloakGetError as e:
        logger.exception(e)
        return Response(e.response_body, e.response_code)
    except Exception as e:
        logger.exception(e)
        return {'error': str(e)}, 400


def update_group(id, body):
    try:
        g.keycloak.group_udate(id, body)
        logger.info(f'Updated group {id}')
        return g.keycloak.group_get(id), 200
    except KeycloakGetError as e:
        logger.exception(e)
        return Response(e.response_body, e.response_code)
    except Exception as e:
        logger.exception(e)
        return {'error': str(e)}, 400


def delete_group(id):
    try:
        g.keycloak.group_delete(id)
        logger.info(f'Deleted group {id}')
        return {}, 200
    except KeycloakGetError as e:
        logger.exception(e)
        return Response(e.response_body, e.response_code)
    except Exception as e:
        logger.exception(e)
        return {'error': str(e)}, 400


def list_group_users(id):
    try:
        return g.keycloak.group_user_list(id), 200
    except KeycloakGetError as e:
        logger.exception(e)
        return Response(e.response_body, e.response_code)
    except Exception as e:
        logger.exception(e)
        return {'error': str(e)}, 400


def list_group_roles(id):
    raise NotImplementedError


def add_group_role(id, body):
    raise NotImplementedError


def delete_group_role(id, body):
    raise NotImplementedError
