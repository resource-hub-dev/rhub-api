import logging

from flask import g, Response
from keycloak import KeycloakGetError


logger = logging.getLogger(__name__)


def list_users():
    try:
        return g.keycloak.user_list({}), 200
    except KeycloakGetError as e:
        logger.exception(e)
        return Response(e.response_body, e.response_code)
    except Exception as e:
        logger.exception(e)
        return {'error': str(e)}, 400


def create_user(body):
    try:
        user_id = g.keycloak.user_create(body)
        logger.info(f'Created user {user_id}')
        return g.keycloak.user_get(user_id), 200
    except KeycloakGetError as e:
        logger.exception(e)
        return Response(e.response_body, e.response_code)
    except Exception as e:
        logger.exception(e)
        return {'error': str(e)}, 400


def get_user(id):
    try:
        return g.keycloak.user_get(id), 200
    except KeycloakGetError as e:
        logger.exception(e)
        return Response(e.response_body, e.response_code)
    except Exception as e:
        logger.exception(e)
        return {'error': str(e)}, 400


def update_user(id, body):
    try:
        g.keycloak.user_update(id, body)
        logger.info(f'Updated user {id}')
        return g.keycloak.user_get(id), 200
    except KeycloakGetError as e:
        logger.exception(e)
        return Response(e.response_body, e.response_code)
    except Exception as e:
        logger.exception(e)
        return {'error': str(e)}, 400


def delete_user(id):
    try:
        g.keycloak.user_delete(id)
        logger.info(f'Deleted user {id}')
        return {}, 200
    except KeycloakGetError as e:
        logger.exception(e)
        return Response(e.response_body, e.response_code)
    except Exception as e:
        logger.exception(e)
        return {'error': str(e)}, 400


def list_user_groups(id):
    try:
        return g.keycloak.user_group_list(id), 200
    except KeycloakGetError as e:
        logger.exception(e)
        return Response(e.response_body, e.response_code)
    except Exception as e:
        logger.exception(e)
        return {'error': str(e)}, 400


def add_user_group(id, body):
    try:
        g.keycloak.group_user_add(id, body['id'])
        return {}, 200
    except KeycloakGetError as e:
        logger.exception(e)
        return Response(e.response_body, e.response_code)
    except Exception as e:
        logger.exception(e)
        return {'error': str(e)}, 400


def delete_user_group(id, body):
    try:
        g.keycloak.group_user_remove(id, body['id'])
        return {}, 200
    except KeycloakGetError as e:
        logger.exception(e)
        return Response(e.response_body, e.response_code)
    except Exception as e:
        logger.exception(e)
        return {'error': str(e)}, 400


def list_user_roles(id):
    raise NotImplementedError


def add_user_role(id, body):
    raise NotImplementedError


def delete_user_role(id, body):
    raise NotImplementedError


def get_current_user(user):
    try:
        return g.keycloak.user_get(user), 200
    except KeycloakGetError as e:
        logger.exception(e)
        return Response(e.response_body, e.response_code)
    except Exception as e:
        logger.exception(e)
        return {'error': str(e)}, 400
