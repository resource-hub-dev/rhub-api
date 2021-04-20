import base64

import pytest

from rhub.api import create_app
from rhub.auth.keycloak import KeycloakClient


API_BASE = '/v0'


@pytest.fixture
def client():
    app = create_app()
    flask_app = app.app

    with flask_app.test_client() as client:
        yield client


@pytest.fixture
def keycloak_mock(mocker):
    keycloak_mock = mocker.Mock(spec=KeycloakClient)

    for m in ['token', 'user', 'group']:
        get_keycloak_mock = mocker.patch(f'rhub.api.auth.{m}.get_keycloak')
        get_keycloak_mock.return_value = keycloak_mock

    yield keycloak_mock


def test_token_create(client, keycloak_mock):
    keycloak_mock.login.return_value = {'access_token': 'foobar'}

    rv = client.post(
        f'{API_BASE}/auth/token/create',
        headers={
            'Authorization': 'Basic ' + base64.b64encode(b'user:pass').decode(),
        }
    )

    keycloak_mock.login.assert_called_with('user', 'pass')

    assert rv.status_code == 200
    assert rv.json == {'access_token': 'foobar'}


def test_me(client, keycloak_mock):
    keycloak_mock.user_get.return_value = {'username': 'user'}

    rv = client.get(
        f'{API_BASE}/me',
        headers={'Authorization': 'Bearer foobar'},
    )

    assert rv.status_code == 200
    assert rv.json == {'username': 'user'}


def test_list_users(client, keycloak_mock):
    keycloak_mock.user_list.return_value = [{'username': 'user'}]

    rv = client.get(
        f'{API_BASE}/auth/user',
        headers={'Authorization': 'Bearer foobar'},
    )

    keycloak_mock.user_list.assert_called_with({})

    assert rv.status_code == 200
    assert rv.json == [{'username': 'user'}]


def test_create_user(client, keycloak_mock):
    user_id = 'uuid'
    user_data = {'username': 'user', 'email': 'user@example.com'}

    keycloak_mock.user_create.return_value = user_id
    keycloak_mock.user_get.return_value = user_data

    rv = client.post(
        f'{API_BASE}/auth/user',
        headers={'Authorization': 'Bearer foobar'},
        json=user_data,
    )

    keycloak_mock.user_create.assert_called_with(user_data)
    keycloak_mock.user_get.assert_called_with(user_id)

    assert rv.status_code == 200
    assert rv.json == user_data


def test_get_user(client, keycloak_mock):
    user_id = 'uuid'
    user_data = {'username': 'user', 'email': 'user@example.com'}

    keycloak_mock.user_get.return_value = user_data

    rv = client.get(
        f'{API_BASE}/auth/user/{user_id}',
        headers={'Authorization': 'Bearer foobar'},
    )

    keycloak_mock.user_get.assert_called_with(user_id)

    assert rv.status_code == 200
    assert rv.json == user_data


def test_update_user(client, keycloak_mock):
    user_id = 'uuid'
    user_data = {'username': 'user', 'email': 'new-user@example.com'}

    keycloak_mock.user_update.return_value = user_id
    keycloak_mock.user_get.return_value = user_data

    rv = client.patch(
        f'{API_BASE}/auth/user/{user_id}',
        headers={'Authorization': 'Bearer foobar'},
        json=user_data,
    )

    keycloak_mock.user_update.assert_called_with(user_id, user_data)
    keycloak_mock.user_get.assert_called_with(user_id)

    assert rv.status_code == 200
    assert rv.json == user_data


def test_delete_user(client, keycloak_mock):
    user_id = 'uuid'

    keycloak_mock.user_delete.return_value = None

    rv = client.delete(
        f'{API_BASE}/auth/user/{user_id}',
        headers={'Authorization': 'Bearer foobar'},
    )

    keycloak_mock.user_delete.assert_called_with(user_id)

    assert rv.status_code == 200
    assert rv.json == {}

def test_list_user_groups(client, keycloak_mock):
    user_id = 'uuid'

    keycloak_mock.user_group_list.return_value = [{'name': 'admin'}]

    rv = client.get(
        f'{API_BASE}/auth/user/{user_id}/groups',
        headers={'Authorization': 'Bearer foobar'},
    )

    keycloak_mock.user_group_list.assert_called_with(user_id)

    assert rv.status_code == 200
    assert rv.json == [{'name': 'admin'}]


def test_add_user_group(client, keycloak_mock):
    user_id = 'uuid'
    group_id = 'ugid'

    keycloak_mock.group_user_add.return_value = None

    rv = client.post(
        f'{API_BASE}/auth/user/{user_id}/groups',
        headers={'Authorization': 'Bearer foobar'},
        json={'id': group_id},
    )

    keycloak_mock.group_user_add.assert_called_with(user_id, group_id)

    assert rv.status_code == 200
    assert rv.json == {}


def test_delete_user_group(client, keycloak_mock):
    user_id = 'uuid'
    group_id = 'ugid'

    keycloak_mock.group_user_remove.return_value = None

    rv = client.delete(
        f'{API_BASE}/auth/user/{user_id}/groups',
        headers={'Authorization': 'Bearer foobar'},
        json={'id': group_id},
    )

    keycloak_mock.group_user_remove.assert_called_with(user_id, group_id)

    assert rv.status_code == 200
    assert rv.json == {}


def test_list_groups(client, keycloak_mock):
    keycloak_mock.group_list.return_value = [{'name': 'admin'}]

    rv = client.get(
        f'{API_BASE}/auth/group',
        headers={'Authorization': 'Bearer foobar'},
    )

    assert rv.status_code == 200
    assert rv.json == [{'name': 'admin'}]


def test_create_group(client, keycloak_mock):
    group_id = 'uuid'
    group_data = {'name': 'admin'}

    keycloak_mock.group_create.return_value = group_id
    keycloak_mock.group_get.return_value = group_data

    rv = client.post(
        f'{API_BASE}/auth/group',
        headers={'Authorization': 'Bearer foobar'},
        json=group_data,
    )

    keycloak_mock.group_create.assert_called_with(group_data)
    keycloak_mock.group_get.assert_called_with(group_id)

    assert rv.status_code == 200
    assert rv.json == group_data


def test_get_group(client, keycloak_mock):
    group_id = 'uuid'
    group_data = {'name': 'admin'}

    keycloak_mock.group_get.return_value = group_data

    rv = client.get(
        f'{API_BASE}/auth/group/{group_id}',
        headers={'Authorization': 'Bearer foobar'},
    )

    keycloak_mock.group_get.assert_called_with(group_id)

    assert rv.status_code == 200
    assert rv.json == group_data


def test_update_group(client, keycloak_mock):
    group_id = 'uuid'
    group_data = {'name': 'new-admin'}

    keycloak_mock.group_update.return_value = group_id
    keycloak_mock.group_get.return_value = group_data

    rv = client.patch(
        f'{API_BASE}/auth/group/{group_id}',
        headers={'Authorization': 'Bearer foobar'},
        json=group_data,
    )

    keycloak_mock.group_update.assert_called_with(group_id, group_data)
    keycloak_mock.group_get.assert_called_with(group_id)

    assert rv.status_code == 200
    assert rv.json == group_data


def test_delete_group(client, keycloak_mock):
    group_id = 'uuid'

    keycloak_mock.group_delete.return_value = group_id

    rv = client.delete(
        f'{API_BASE}/auth/group/{group_id}',
        headers={'Authorization': 'Bearer foobar'},
    )

    keycloak_mock.group_delete.assert_called_with(group_id)

    assert rv.status_code == 200
    assert rv.json == {}


def test_list_group_users(client, keycloak_mock):
    group_id = 'uuid'
    user_list = [{'username': 'user'}]

    keycloak_mock.group_user_list.return_value = user_list

    rv = client.get(
        f'{API_BASE}/auth/group/{group_id}/users',
        headers={'Authorization': 'Bearer foobar'},
    )

    keycloak_mock.group_user_list.assert_called_with(group_id)

    assert rv.status_code == 200
    assert rv.json == user_list
