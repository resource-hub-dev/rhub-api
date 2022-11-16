import logging

from connexion import problem
from flask import url_for

from rhub.api import DEFAULT_PAGE_LIMIT
from rhub.api.utils import db_sort
from rhub.auth import model


logger = logging.getLogger(__name__)


def _group_href(group):
    return {
        'group': url_for('.rhub_api_auth_group_group_get',
                         group_id=group.id),
    }


def group_list(filter_, sort=None, page=0, limit=DEFAULT_PAGE_LIMIT):
    groups = model.Group.query

    if 'name' in filter_:
        groups = groups.filter(model.Group.name.ilike(filter_['name']))

    if 'user_id' in filter_ or 'user_name' in filter_:
        groups = groups.join(model.User, model.Group.users)

        if 'user_id' in filter_:
            groups = groups.filter(model.User.id == filter_['user_id'])

        if 'group_name' in filter_:
            groups = groups.filter(model.User.name == filter_['user_name'])

    if sort:
        groups = db_sort(groups, sort)

    return {
        'data': [
            group.to_dict() | {'_href': _group_href(group)}
            for group in groups.limit(limit).offset(page * limit)
        ],
        'total': groups.count(),
    }


def group_get(group_id):
    group_row = model.Group.query.get(group_id)
    if not group_row:
        return problem(404, 'Not Found', f'Group {group_id} does not exist')
    return group_row.to_dict() | {'_href': _group_href(group_row)}
