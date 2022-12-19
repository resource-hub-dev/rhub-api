import datetime
import logging

from flask import current_app
from oic import oic
from werkzeug.exceptions import Unauthorized

from rhub.api import db, di
from rhub.api.utils import date_now
from rhub.auth import ldap
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

    if token_row.is_expired:
        logger.error(f'token ID={token_row.id} has expired')
        raise Unauthorized('Token has expired.')

    return {'uid': token_row.user_id}


def bearer_auth(token):
    logger = logging.getLogger(f'{__name__}.bearer_auth')

    oidc_endpoint = current_app.config.get('AUTH_OIDC_ENDPOINT')
    if not oidc_endpoint:
        logger.warning('OIDC auth is disabled')
        raise Unauthorized()

    try:
        client = oic.Client()
        client.provider_config(oidc_endpoint)

        user_info = client.do_user_info_request(token=token)
        if 'error' in user_info:
            logger.error(f'invalid token, {user_info["error_description"]}')
            raise Unauthorized()

        external_uuid = user_info['sub']

        user_row = auth_model.User.query.filter(
            auth_model.User.external_uuid == external_uuid
        ).first()

        try:
            ldap_client = di.get(ldap.LdapClient)
            user_row = _user_sync(ldap_client, external_uuid, user_row)
        except Exception:
            logger.exception('failed to sync user data from LDAP')

        if not user_row:
            raise Unauthorized()

        return {'uid': user_row.id}

    except Exception:
        logger.exception('OIDC auth failed')
        raise Unauthorized()


def _user_sync(ldap_client, external_uuid, user_row):
    logger = logging.getLogger(f'{__name__}.user_sync')

    if user_row:
        update_threshold = date_now() - datetime.timedelta(hours=12)
        if user_row.updated_at < update_threshold:
            logger.info(
                f'user with {external_uuid=} exists, will try to update data from LDAP'
            )
            user_row.update_from_ldap(ldap_client)
            db.session.commit()
            logger.info(f'updated user ID={user_row.id} {external_uuid=} in the DB')

    else:
        logger.info(
            f'user with {external_uuid=} does not exist, will try to '
            'create it from LDAP'
        )
        user_row = auth_model.User.create_from_ldap(ldap_client, external_uuid)
        db.session.add(user_row)
        db.session.commit()
        logger.info(f'created user ID={user_row.id} {external_uuid=} in the DB')

    return user_row
