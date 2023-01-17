import logging

from connexion import problem
from flask import url_for

from rhub.api import DEFAULT_PAGE_LIMIT
from rhub.api.utils import db_sort
from rhub.auth import model


logger = logging.getLogger(__name__)


def _user_href(user):
    href = {
        'user': url_for('.rhub_api_auth_user_user_get',
                        user_id=user.id),
    }
    if user.manager_id:
        href['manager'] = url_for('.rhub_api_auth_user_user_get',
                                  user_id=user.manager_id)
    return href


def user_list(filter_, sort=None, page=0, limit=DEFAULT_PAGE_LIMIT):
    users = model.User.query.filter(model.User.deleted.is_(False))

    if 'name' in filter_:
        users = users.filter(model.User.name.ilike(filter_['name']))

    if 'group_id' in filter_ or 'group_name' in filter_:
        users = users.join(model.Group, model.User.groups)

        if 'group_id' in filter_:
            users = users.filter(model.Group.id == filter_['group_id'])

        if 'group_name' in filter_:
            users = users.filter(model.Group.name == filter_['group_name'])

    if sort:
        users = db_sort(users, sort)

    return {
        'data': [
            user.to_dict() | {'_href': _user_href(user)}
            for user in users.limit(limit).offset(page * limit)
        ],
        'total': users.count(),
    }


def user_get(user_id):
    user_row = model.User.query.get(user_id)
    if not user_row or user_row.deleted:
        return problem(404, 'Not Found', f'User {user_id} does not exist')
    return user_row.to_dict() | {'_href': _user_href(user_row)}


def user_ssh_keys(user_id):
    user_row = model.User.query.get(user_id)
    if not user_row or user_row.deleted:
        return problem(404, 'Not Found', f'User {user_id} does not exist')
    return '\n'.join(user_row.ssh_keys) + '\n'


def get_current_user(user):
    return user_get(user)
