import logging

from connexion import problem

from rhub.api import db
from rhub.api.utils import date_now, date_parse
from rhub.auth import model, utils


logger = logging.getLogger(__name__)


def token_list(user_id, user):
    user_row = model.User.query.get(user_id)
    if not user_row or user_row.deleted:
        return problem(404, 'Not Found', f'User ID={user_id} does not exist')

    if not (utils.user_is_admin(user) or user_id == user):
        return problem(
            403, 'Forbidden',
            "You don't have permission to list other users' tokens."
        )

    tokens = model.Token.query.filter(model.Token.user_id == user_id)

    return {
        'data': [token.to_dict() for token in tokens.all()],
        'total': tokens.count(),
    }


def token_create(user_id, body, user):
    user_row = model.User.query.get(user_id)
    if not user_row or user_row.deleted:
        return problem(404, 'Not Found', f'User ID={user_id} does not exist')

    if not (utils.user_is_admin(user) or user_id == user):
        return problem(
            403, 'Forbidden',
            "You don't have permission to create tokens for other users."
        )

    token_data = {'user_id': user_id} | body

    if token_data.get('expires_at'):
        try:
            expires_at = date_parse(token_data['expires_at'])
            token_data['expires_at'] = expires_at
        except Exception:
            expires_at = None

        if not expires_at or expires_at < date_now():
            return problem(400, 'Bad Request', 'Invalid expiration date.')

    token_plain, token = model.Token.generate(**token_data)

    db.session.add(token)
    db.session.commit()

    return token.to_dict() | {'token': token_plain}


def token_delete(user_id, token_id, user):
    user_row = model.User.query.get(user_id)
    if not user_row or user_row.deleted:
        return problem(404, 'Not Found', f'User ID={user_id} does not exist')

    token_row = model.Token.query.get(token_id)
    if not token_row or token_row.user_id != user_id:
        return problem(
            404, 'Not Found',
            f'Token ID={token_id} does not exist or is not owned by user ID={user_id}.'
        )

    if not (utils.user_is_admin(user) or user_id == user):
        return problem(
            403, 'Forbidden',
            "You don't have permission to delete other users' tokens."
        )

    db.session.delete(token_row)
    db.session.commit()
