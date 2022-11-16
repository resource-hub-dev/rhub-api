import logging

from flask import current_app
from werkzeug.exceptions import Unauthorized
from oic import oic

from rhub.auth import model as auth_model


def basic_auth(username, password):
    logger = logging.getLogger(f'{__name__}.basic_auth')

    if username != '__token__':
        logger.error("invalid username, only '__token__' is valid")
        raise Unauthorized()

    token_row = auth_model.Token.find(password)
    if not token_row:
        logger.error('token does not exist in the DB')
        raise Unauthorized()

    return {'uid': token_row.user_id}


def bearer_auth(token):
    logger = logging.getLogger(f'{__name__}.bearer_auth')

    client = oic.Client()
    client.provider_config(current_app.config['AUTH_OIDC_ENDPOINT'])

    user_info = client.do_user_info_request(token=token)
    if 'error' in user_info:
        logger.error(f'invalid token, {user_info["error_description"]}')
        raise Unauthorized()

    external_uuid = user_info['sub']

    user_query = auth_model.User.query.filter(
        auth_model.User.external_uuid == external_uuid
    )
    if user_query.count() != 1:
        logger.error(f'user with {external_uuid=} does not exist')
        raise Unauthorized()

    user = user_query.first()
    return {'uid': user.id}
