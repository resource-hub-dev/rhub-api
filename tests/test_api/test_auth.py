import base64
import datetime
from unittest.mock import ANY

import pytest
from dateutil.tz import tzutc

from rhub.api import DEFAULT_PAGE_LIMIT
from rhub.auth import model


API_BASE = '/v0'
AUTH_HEADER = {'Authorization': 'Basic X190b2tlbl9fOmR1bW15Cg=='}

SSH_KEY = 'ssh-ed25519 AAAAexamplesshkeyexamplesshkeyexamplesshkeyABCD'
DATE = datetime.datetime(2021, 1, 1, 1, 0, 0, tzinfo=tzutc())
DATE_STR = '2021-01-01T01:00:00+00:00'


def test_me(client):
    model.User.query.get.return_value = model.User(
        id=1,
        external_uuid=None,
        ldap_dn=None,
        name='test',
        email='test@example.com',
        ssh_keys=[SSH_KEY],
        created_at=DATE,
        updated_at=DATE,
    )

    rv = client.get(
        f'{API_BASE}/me',
        headers=AUTH_HEADER,
    )

    assert rv.status_code == 200
    assert rv.json == {
        'id': 1,
        'external_uuid': None,
        'ldap_dn': None,
        'name': 'test',
        'email': 'test@example.com',
        'ssh_keys': [SSH_KEY],
        'created_at': DATE_STR,
        'updated_at': DATE_STR,
        '_href': ANY,
    }


def test_list_users(client):
    model.User.query.limit.return_value.offset.return_value = [
        model.User(
            id=1,
            external_uuid=None,
            ldap_dn=None,
            name='test',
            email='test@example.com',
            ssh_keys=[SSH_KEY],
            created_at=DATE,
            updated_at=DATE,
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
                'ldap_dn': None,
                'name': 'test',
                'email': 'test@example.com',
                'ssh_keys': [SSH_KEY],
                'created_at': DATE_STR,
                'updated_at': DATE_STR,
                '_href': ANY,
            },
        ],
        'total': 1,
    }


def test_get_user(client):
    model.User.query.get.return_value = model.User(
        id=1,
        external_uuid=None,
        ldap_dn=None,
        name='test',
        email='test@example.com',
        ssh_keys=[SSH_KEY],
        created_at=DATE,
        updated_at=DATE,
    )

    rv = client.get(
        f'{API_BASE}/auth/user/1',
        headers=AUTH_HEADER,
    )

    assert rv.status_code == 200
    assert rv.json == {
        'id': 1,
        'external_uuid': None,
        'ldap_dn': None,
        'name': 'test',
        'email': 'test@example.com',
        'ssh_keys': [SSH_KEY],
        'created_at': DATE_STR,
        'updated_at': DATE_STR,
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


def test_list_groups(client):
    model.Group.query.limit.return_value.offset.return_value = [
        model.Group(
            id=1,
            name='test',
            ldap_dn=None,
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
                'ldap_dn': None,
                '_href': ANY,
            },
        ],
        'total': 1,
    }


def test_get_group(client):
    model.Group.query.get.return_value = model.Group(
        id=1,
        name='test',
        ldap_dn=None,
    )

    rv = client.get(
        f'{API_BASE}/auth/group/1',
        headers=AUTH_HEADER,
    )

    assert rv.status_code == 200
    assert rv.json == {
        'id': 1,
        'name': 'test',
        'ldap_dn': None,
        '_href': ANY,
    }
