import logging

from connexion import problem

from rhub.auth import model, utils


logger = logging.getLogger(__name__)


def token_list(user_id, user):
    if not utils.user_is_admin(user_id) or user_id != user:
        return problem(
            403, 'Forbidden',
            "You don't have permission to list other users' tokens."
        )

    tokens = model.Token.query.filter(model.Token.user_id == user_id)

    return {
        'data': [token.to_dict() for token in tokens.all()],
        'total': tokens.count(),
    }
