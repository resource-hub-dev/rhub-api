from flask import g, request, Response
from keycloak import KeycloakGetError


def decode_token(token):
    return g.keycloak.token_info(token)


def basic_auth(username, password, required_scopes=None):
    return g.keycloak.login(username, password)


def get_token_info():
    # Bearer auth is enforced by connexion (see openapi spec)
    _, access_token = request.headers['Authorization'].split()

    try:
        return g.keycloak.token_info(access_token), 200
    except KeycloakGetError as e:
        return Response(e.response_body, e.response_code)
    except Exception as e:
        return {'error': str(e)}, 400


def create_token():
    if not request.authorization:
        return {'error': 'Missing credentials'}, 400

    username = request.authorization['username']
    password = request.authorization['password']

    try:
        return g.keycloak.login(username, password), 200
    except KeycloakGetError as e:
        return Response(e.response_body, e.response_code)
    except Exception as e:
        return {'error': str(e)}, 400


def refresh_token():
    if 'Authorization' not in request.headers:
        return {'error': 'Missing token'}, 400

    try:
        _, refresh_token = request.headers['Authorization'].split()
    except Exception:
        return {'error': 'Invalid token'}, 400

    try:
        return g.keycloak.token_refresh(refresh_token), 200
    except KeycloakGetError as e:
        return Response(e.response_body, e.response_code)
    except Exception as e:
        return {'error': str(e)}, 400
