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
DATE = datetime.datetime(2100, 1, 1, 1, 0, 0, tzinfo=tzutc())
DATE_STR = '2100-01-01T01:00:00+00:00'


@pytest.fixture
def user_is_admin_mock(mocker):
    yield mocker.patch('rhub.auth.utils.user_is_admin')


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
            name='test token',
            created_at=DATE,
            expires_at=DATE,
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
                'name': 'test token',
                'created_at': DATE_STR,
                'expires_at': DATE_STR,
            },
        ],
        'total': 1,
    }


@pytest.mark.parametrize('expires_at', [None, DATE_STR])
def test_create_token(client, db_session_mock, expires_at):
    token_data = {
        'name': 'test token',
        'expires_at': expires_at,
    }

    def db_add(row):
        row.id = 1
        row.created_at = DATE

    db_session_mock.add.side_effect = db_add

    rv = client.post(
        f'{API_BASE}/auth/user/1/token',
        headers=AUTH_HEADER,
        json=token_data,
    )

    assert rv.status_code == 200
    assert rv.json == {
        'id': 1,
        'name': 'test token',
        'created_at': DATE_STR,
        'expires_at': expires_at,
        'token': ANY,
    }

    db_session_mock.add.assert_called()
    db_session_mock.commit.assert_called()


@pytest.mark.parametrize('expires_at', ['foobar', '1970-01-01T12:00:00Z'])
def test_create_token_invalid_expiration(client, db_session_mock, expires_at):
    token_data = {
        'expires_at': expires_at,
    }

    def db_add(row):
        row.id = 1
        row.created_at = DATE

    db_session_mock.add.side_effect = db_add

    rv = client.post(
        f'{API_BASE}/auth/user/1/token',
        headers=AUTH_HEADER,
        json=token_data,
    )

    assert rv.status_code == 400
    assert rv.json['detail'] == 'Invalid expiration date.'

    db_session_mock.add.assert_not_called()
    db_session_mock.commit.assert_not_called()


def test_delete_token(client, db_session_mock, user_is_admin_mock):
    token_row = model.Token(
        id=1,
        user_id=1,
        name='test token',
        created_at=DATE,
        expires_at=DATE,
    )
    model.Token.query.get.return_value = token_row

    user_is_admin_mock.return_value = True

    rv = client.delete(
        f'{API_BASE}/auth/user/1/token/1',
        headers=AUTH_HEADER,
    )

    assert rv.status_code == 204

    db_session_mock.delete.assert_called_with(token_row)
    db_session_mock.commit.assert_called()


def test_delete_token_forbidden(client, db_session_mock, user_is_admin_mock):
    token_row = model.Token(
        id=1,
        user_id=1234,
        name='test token',
        created_at=DATE,
        expires_at=DATE,
    )
    model.Token.query.get.return_value = token_row

    user_is_admin_mock.return_value = False

    rv = client.delete(
        f'{API_BASE}/auth/user/1234/token/1',
        headers=AUTH_HEADER,
    )

    assert rv.status_code == 403

    db_session_mock.delete.assert_not_called()
    db_session_mock.commit.assert_not_called()


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
