from flask import g, Response
from keycloak import KeycloakGetError


def list_users():
    raise NotImplementedError


def create_user(body):
    raise NotImplementedError


def get_user(id):
    raise NotImplementedError


def update_user(id, body):
    raise NotImplementedError


def delete_user(id):
    raise NotImplementedError


def list_user_groups(id):
    raise NotImplementedError


def add_user_group(id, body):
    raise NotImplementedError


def delete_user_group(id):
    raise NotImplementedError


def list_user_roles(id):
    raise NotImplementedError


def add_user_role(id, body):
    raise NotImplementedError


def delete_user_role(id, body):
    raise NotImplementedError


def get_current_user(user):
    try:
        return g.keycloak.user_info(user), 200
    except KeycloakGetError as e:
        return Response(e.response_body, e.response_code)
    except Exception as e:
        return {'error': str(e)}, 400
