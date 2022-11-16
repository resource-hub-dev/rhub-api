import base64
from unittest.mock import ANY

import pytest

from rhub.auth.keycloak import KeycloakClient
from rhub.api import DEFAULT_PAGE_LIMIT
from rhub.auth import model


API_BASE = '/v0'
AUTH_HEADER = {'Authorization': 'Basic X190b2tlbl9fOmR1bW15Cg=='}


def test_me(client):
    model.User.query.get.return_value = model.User(
        id=1,
        name='test',
    )

    rv = client.get(
        f'{API_BASE}/me',
        headers=AUTH_HEADER,
    )

    assert rv.status_code == 200
    assert rv.json == {
        'id': 1,
        'external_uuid': None,
        'name': 'test',
        '_href': ANY,
    }


def test_list_users(client):
    model.User.query.limit.return_value.offset.return_value = [
        model.User(
            id=1,
            name='test',
        )
    ]
    model.User.query.count.return_value = 1

    rv = client.get(
        f'{API_BASE}/auth/user',
        headers=AUTH_HEADER,
    )

    assert rv.status_code == 200
    assert rv.json == {
        'data': [
            {
                'id': 1,
                'external_uuid': None,
                'name': 'test',
                '_href': ANY,
            },
        ],
        'total': 1,
    }


def test_get_user(client):
    model.User.query.get.return_value = model.User(
        id=1,
        name='test',
    )

    rv = client.get(
        f'{API_BASE}/auth/user/1',
        headers=AUTH_HEADER,
    )

    assert rv.status_code == 200
    assert rv.json == {
        'id': 1,
        'external_uuid': None,
        'name': 'test',
        '_href': ANY,
    }


def test_list_token(client):
    model.Token.query.filter.return_value.all.return_value = [
        model.Token(
            id=1,
        ),
    ]
    model.Token.query.filter.return_value.count.return_value = 1

    rv = client.get(
        f'{API_BASE}/auth/user/1/token',
        headers=AUTH_HEADER,
    )

    assert rv.status_code == 200
    assert rv.json == {
        'data': [
            {
                'id': 1,
            },
        ],
        'total': 1,
    }


def test_list_groups(client, keycloak_mock):
    model.Group.query.limit.return_value.offset.return_value = [
        model.Group(
            id=1,
            name='test',
        )
    ]
    model.Group.query.count.return_value = 1

    rv = client.get(
        f'{API_BASE}/auth/group',
        headers=AUTH_HEADER,
    )

    assert rv.status_code == 200
    assert rv.json == {
        'data': [
            {
                'id': 1,
                'name': 'test',
                '_href': ANY,
            },
        ],
        'total': 1,
    }


def test_get_group(client, keycloak_mock):
    model.Group.query.get.return_value = model.Group(
        id=1,
        name='test',
    )

    rv = client.get(
        f'{API_BASE}/auth/group/1',
        headers=AUTH_HEADER,
    )

    assert rv.status_code == 200
    assert rv.json == {
        'id': 1,
        'name': 'test',
        '_href': ANY,
    }
