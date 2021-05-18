import logging

from flask import request
from connexion import problem
from keycloak import KeycloakGetError

from rhub.api import get_keycloak
from rhub.auth.keycloak import problem_from_keycloak_error


logger = logging.getLogger(__name__)


def decode_token(token):
    return get_keycloak().token_info(token)


def basic_auth(username, password, required_scopes=None):
    return get_keycloak().login(username, password)


def get_token_info():
    # Bearer auth is enforced by connexion (see openapi spec)
    _, access_token = request.headers['Authorization'].split()

    try:
        return get_keycloak().token_info(access_token), 200
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


def create_token():
    if not request.authorization:
        return problem(401, 'Unauthorized', 'Missing basic auth credentials')

    username = request.authorization['username']
    password = request.authorization['password']

    try:
        return get_keycloak().login(username, password), 200
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))


def refresh_token():
    if 'Authorization' not in request.headers:
        return problem(401, 'Unauthorized', 'Missing refresh token')

    try:
        _, refresh_token = request.headers['Authorization'].split()
    except Exception:
        return problem(401, 'Unauthorized', 'Invalid token')

    try:
        return get_keycloak().token_refresh(refresh_token), 200
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error', str(e))
