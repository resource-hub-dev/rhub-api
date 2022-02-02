import base64
from unittest.mock import ANY

import pytest

from rhub.auth.keycloak import KeycloakClient
from rhub.api import DEFAULT_PAGE_LIMIT


API_BASE = '/v0'


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
    keycloak_mock.user_get.return_value = {
        'id': '00000000-0000-0000-0000-000000000000',
        'username': 'user',
    }

    rv = client.get(
        f'{API_BASE}/me',
        headers={'Authorization': 'Bearer foobar'},
    )

    assert rv.status_code == 200
    assert rv.json == {
        'id': '00000000-0000-0000-0000-000000000000',
        'username': 'user',
        '_href': ANY,
    }


def test_list_users(client, keycloak_mock):
    keycloak_mock.user_list.return_value = [{
        'id': '00000000-0000-0000-0000-000000000000',
        'username': 'user',
    }]

    rv = client.get(
        f'{API_BASE}/auth/user',
        headers={'Authorization': 'Bearer foobar'},
    )

    keycloak_mock.user_list.assert_called_with({'first': 0, 'max': DEFAULT_PAGE_LIMIT})

    assert rv.status_code == 200
    assert rv.json == [{
        'id': '00000000-0000-0000-0000-000000000000',
        'username': 'user',
        '_href': ANY,
    }]


def test_create_user(client, keycloak_mock):
    user_id = '00000000-0000-0000-0000-000000000000'
    user_data = {'username': 'user', 'email': 'user@example.com'}

    keycloak_mock.user_create.return_value = user_id
    keycloak_mock.user_get.return_value = user_data | {'id': user_id}

    rv = client.post(
        f'{API_BASE}/auth/user',
        headers={'Authorization': 'Bearer foobar'},
        json=user_data,
    )

    keycloak_mock.user_create.assert_called_with(user_data)
    keycloak_mock.user_get.assert_called_with(user_id)

    assert rv.status_code == 200
    assert rv.json == user_data | {'id': user_id, '_href': ANY}


def test_get_user(client, keycloak_mock):
    user_id = '00000000-0000-0000-0000-000000000000'
    user_data = {'username': 'user', 'email': 'user@example.com'}

    keycloak_mock.user_get.return_value = user_data | {'id': user_id}

    rv = client.get(
        f'{API_BASE}/auth/user/{user_id}',
        headers={'Authorization': 'Bearer foobar'},
    )

    keycloak_mock.user_get.assert_called_with(user_id)

    assert rv.status_code == 200
    assert rv.json == user_data | {'id': user_id, '_href': ANY}


def test_update_user(client, keycloak_mock):
    user_id = '00000000-0000-0000-0000-000000000000'
    user_data = {'username': 'user', 'email': 'new-user@example.com'}

    keycloak_mock.user_update.return_value = user_id
    keycloak_mock.user_get.return_value = user_data | {'id': user_id}

    rv = client.patch(
        f'{API_BASE}/auth/user/{user_id}',
        headers={'Authorization': 'Bearer foobar'},
        json=user_data,
    )

    keycloak_mock.user_update.assert_called_with(user_id, user_data)
    keycloak_mock.user_get.assert_called_with(user_id)

    assert rv.status_code == 200
    assert rv.json == user_data | {'id': user_id, '_href': ANY}


def test_delete_user(client, keycloak_mock):
    user_id = '00000000-0000-0000-0000-000000000000'

    keycloak_mock.user_delete.return_value = None

    rv = client.delete(
        f'{API_BASE}/auth/user/{user_id}',
        headers={'Authorization': 'Bearer foobar'},
    )

    keycloak_mock.user_delete.assert_called_with(user_id)

    assert rv.status_code == 200
    assert rv.json == {}

def test_list_user_groups(client, keycloak_mock):
    user_id = '00000000-0000-0000-0000-000000000000'

    keycloak_mock.user_group_list.return_value = [{'id': user_id, 'name': 'admin'}]

    rv = client.get(
        f'{API_BASE}/auth/user/{user_id}/groups',
        headers={'Authorization': 'Bearer foobar'},
    )

    keycloak_mock.user_group_list.assert_called_with(user_id)

    assert rv.status_code == 200
    assert rv.json == [{'id': user_id, 'name': 'admin', '_href': ANY}]


def test_add_user_group(client, keycloak_mock):
    user_id = '00000000-0000-0000-0000-000000000000'
    group_id = '00000000-0004-0003-0002-000000000001'

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
    user_id = '00000000-0000-0000-0000-000000000000'
    group_id = '00000000-0004-0003-0002-000000000001'

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
    keycloak_mock.group_list.return_value = [{
        'id': '00000000-0000-0000-0000-000000000000',
        'name': 'admin',
    }]

    rv = client.get(
        f'{API_BASE}/auth/group',
        headers={'Authorization': 'Bearer foobar'},
    )

    assert rv.status_code == 200
    assert rv.json == [{
        'id': '00000000-0000-0000-0000-000000000000',
        'name': 'admin',
        '_href': ANY,
    }]


def test_create_group(client, keycloak_mock):
    group_id = '00000000-0004-0003-0002-000000000001'
    group_data = {'name': 'admin'}

    keycloak_mock.group_create.return_value = group_id
    keycloak_mock.group_get.return_value = group_data | {'id': group_id}

    rv = client.post(
        f'{API_BASE}/auth/group',
        headers={'Authorization': 'Bearer foobar'},
        json=group_data,
    )

    keycloak_mock.group_create.assert_called_with(group_data)
    keycloak_mock.group_get.assert_called_with(group_id)

    assert rv.status_code == 200
    assert rv.json == group_data | {'id': group_id, '_href': ANY}


def test_get_group(client, keycloak_mock):
    group_id = '00000000-0004-0003-0002-000000000001'
    group_data = {'name': 'admin'}

    keycloak_mock.group_get.return_value = group_data | {'id': group_id}

    rv = client.get(
        f'{API_BASE}/auth/group/{group_id}',
        headers={'Authorization': 'Bearer foobar'},
    )

    keycloak_mock.group_get.assert_called_with(group_id)

    assert rv.status_code == 200
    assert rv.json == group_data | {'id': group_id, '_href': ANY}


def test_update_group(client, keycloak_mock):
    group_id = '00000000-0004-0003-0002-000000000001'
    group_data = {'name': 'new-admin'}

    keycloak_mock.group_update.return_value = group_id
    keycloak_mock.group_get.return_value = group_data | {'id': group_id}

    rv = client.patch(
        f'{API_BASE}/auth/group/{group_id}',
        headers={'Authorization': 'Bearer foobar'},
        json=group_data,
    )

    keycloak_mock.group_update.assert_called_with(group_id, group_data)
    keycloak_mock.group_get.assert_called_with(group_id)

    assert rv.status_code == 200
    assert rv.json == group_data | {'id': group_id, '_href': ANY}


def test_delete_group(client, keycloak_mock):
    group_id = '00000000-0004-0003-0002-000000000001'

    keycloak_mock.group_delete.return_value = group_id

    rv = client.delete(
        f'{API_BASE}/auth/group/{group_id}',
        headers={'Authorization': 'Bearer foobar'},
    )

    keycloak_mock.group_delete.assert_called_with(group_id)

    assert rv.status_code == 200
    assert rv.json == {}


def test_list_group_users(client, keycloak_mock):
    group_id = '00000000-0004-0003-0002-000000000001'
    user_data = {
        'id': '00000000-0000-0000-0000-000000000000',
        'username': 'user',
    }

    keycloak_mock.group_user_list.return_value = [user_data]

    rv = client.get(
        f'{API_BASE}/auth/group/{group_id}/users',
        headers={'Authorization': 'Bearer foobar'},
    )

    keycloak_mock.group_user_list.assert_called_with(group_id)

    assert rv.status_code == 200
    assert rv.json == [user_data | {'_href': ANY}]


def test_list_roles(client, keycloak_mock):
    keycloak_mock.role_list.return_value = [{
        'id': '00000000-000d-000c-000b-00000000000a',
        'name': 'admin',
    }]

    rv = client.get(
        f'{API_BASE}/auth/role',
        headers={'Authorization': 'Bearer foobar'},
    )

    assert rv.status_code == 200
    assert rv.json == [{
        'id': '00000000-000d-000c-000b-00000000000a',
        'name': 'admin',
        '_href': ANY,
    }]


def test_create_role(client, keycloak_mock):
    role_id = '00000000-000d-000c-000b-00000000000a'
    role_data = {'name': 'admin'}

    keycloak_mock.role_create.return_value = role_id
    keycloak_mock.role_get.return_value = role_data | {'id': role_id}

    rv = client.post(
        f'{API_BASE}/auth/role',
        headers={'Authorization': 'Bearer foobar'},
        json=role_data,
    )

    keycloak_mock.role_create.assert_called_with(role_data)
    keycloak_mock.role_get.assert_called_with(role_id)

    assert rv.status_code == 200
    assert rv.json == role_data | {'id': role_id, '_href': ANY}


def test_get_role(client, keycloak_mock):
    role_id = '00000000-000d-000c-000b-00000000000a'
    role_data = {'name': 'admin'}

    keycloak_mock.role_get.return_value = role_data | {'id': role_id}

    rv = client.get(
        f'{API_BASE}/auth/role/{role_id}',
        headers={'Authorization': 'Bearer foobar'},
    )

    keycloak_mock.role_get.assert_called_with(role_id)

    assert rv.status_code == 200
    assert rv.json == role_data | {'id': role_id, '_href': ANY}


def test_update_role(client, keycloak_mock):
    role_id = '00000000-000d-000c-000b-00000000000a'
    role_data = {'name': 'new-admin'}

    keycloak_mock.role_update.return_value = role_id
    keycloak_mock.role_get.return_value = role_data | {'id': role_id}

    rv = client.patch(
        f'{API_BASE}/auth/role/{role_id}',
        headers={'Authorization': 'Bearer foobar'},
        json=role_data,
    )

    keycloak_mock.role_update.assert_called_with(role_id, role_data)
    keycloak_mock.role_get.assert_called_with(role_data['name'])

    assert rv.status_code == 200
    assert rv.json == role_data | {'id': role_id, '_href': ANY}


def test_delete_role(client, keycloak_mock):
    role_id = '00000000-000d-000c-000b-00000000000a'

    keycloak_mock.role_delete.return_value = role_id

    rv = client.delete(
        f'{API_BASE}/auth/role/{role_id}',
        headers={'Authorization': 'Bearer foobar'},
    )

    keycloak_mock.role_delete.assert_called_with(role_id)

    assert rv.status_code == 200
    assert rv.json == {}
