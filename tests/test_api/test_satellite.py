import base64
from unittest.mock import ANY

import pytest

from rhub.satellite import model


API_BASE = '/v0'


def _db_add_row_side_effect(data_added):
    def side_effect(row):
        for k, v in data_added.items():
            setattr(row, k, v)
    return side_effect


def test_list_servers(client, keycloak_mock):
    model.SatelliteServer.query.limit.return_value.offset.return_value = [
        model.SatelliteServer(
            id=1,
            name='test',
            description='',
            owner_group_id='00000000-0000-0000-0000-000000000000',
            hostname='satellite.example.com',
            insecure=False,
            credentials='kv/test',
        ),
    ]
    model.SatelliteServer.query.count.return_value = 1

    keycloak_mock.group_get_name.return_value = 'test-group'

    rv = client.get(
        f'{API_BASE}/satellite/server',
        headers={'Authorization': 'Bearer foobar'},
    )

    assert rv.status_code == 200, rv.data
    assert rv.json == {
        'data': [
            {
                'id': 1,
                'name': 'test',
                'description': '',
                'owner_group_id': '00000000-0000-0000-0000-000000000000',
                'owner_group_name': 'test-group',
                'hostname': 'satellite.example.com',
                'insecure': False,
                'credentials': 'kv/test',
                '_href': ANY,
            }
        ],
        'total': 1,
    }


def test_list_servers_unauthorized(client):
    rv = client.get(
        f'{API_BASE}/satellite/server',
    )

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_get_server(client, keycloak_mock):
    model.SatelliteServer.query.get.return_value = model.SatelliteServer(
        id=1,
        name='test',
        description='',
        owner_group_id='00000000-0000-0000-0000-000000000000',
        hostname='satellite.example.com',
        insecure=False,
        credentials='kv/test',
    )

    keycloak_mock.group_get_name.return_value = 'test-group'

    rv = client.get(
        f'{API_BASE}/satellite/server/1',
        headers={'Authorization': 'Bearer foobar'},
    )

    model.SatelliteServer.query.get.assert_called_with(1)

    assert rv.status_code == 200, rv.data
    assert rv.json == {
        'id': 1,
        'name': 'test',
        'description': '',
        'owner_group_id': '00000000-0000-0000-0000-000000000000',
        'owner_group_name': 'test-group',
        'hostname': 'satellite.example.com',
        'insecure': False,
        'credentials': 'kv/test',
        '_href': ANY,
    }


def test_get_server_unauthorized(client):
    rv = client.get(
        f'{API_BASE}/satellite/server/1',
    )

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_get_server_non_existent(client):
    server_id = 1

    model.SatelliteServer.query.get.return_value = None

    rv = client.get(
        f'{API_BASE}/satellite/server/{server_id}',
        headers={'Authorization': 'Bearer foobar'},
    )

    model.SatelliteServer.query.get.assert_called_with(server_id)

    assert rv.status_code == 404, rv.data
    assert rv.json['title'] == 'Not Found'
    assert rv.json['detail'] == f'Server {server_id} does not exist'


def test_create_server(client, db_session_mock, keycloak_mock, mocker):
    server_data = {
        'name': 'test',
        'owner_group_id': '00000000-0000-0000-0000-000000000000',
        'hostname': 'satellite.example.com',
        'insecure': True,
        'credentials': 'kv/test',
    }

    model.SatelliteServer.query.filter.return_value.count.return_value = 0
    db_session_mock.add.side_effect = _db_add_row_side_effect({'id': 1})

    keycloak_mock.group_get_name.return_value = 'test-group'

    rv = client.post(
        f'{API_BASE}/satellite/server',
        headers={'Authorization': 'Bearer foobar'},
        json=server_data,
    )

    assert rv.status_code == 200, rv.data

    db_session_mock.add.assert_called()

    server = db_session_mock.add.call_args.args[0]
    for k, v in server_data.items():
        assert getattr(server, k) == v


@pytest.mark.parametrize(
    'server_data, missing_property',
    [
        pytest.param(
            {
                'owner_group_id': '00000000-0000-0000-0000-000000000000',
                'hostname': 'satellite.example.com',
                'insecure': True,
                'credentials': 'kv/test',
            },
            'name',
            id='name'
        ),
        pytest.param(
            {
                'name': 'test',
                'hostname': 'satellite.example.com',
                'insecure': True,
                'credentials': 'kv/test',
            },
            'owner_group_id',
            id='owner_group_id'
        ),
        pytest.param(
            {
                'name': 'test',
                'owner_group_id': '00000000-0000-0000-0000-000000000000',
                'insecure': True,
                'credentials': 'kv/test',
            },
            'hostname',
            id='hostname'
        ),
        pytest.param(
            {
                'name': 'test',
                'owner_group_id': '00000000-0000-0000-0000-000000000000',
                'hostname': 'satellite.example.com',
                'insecure': True,
            },
            'credentials',
            id='credentials'
        ),
    ]
)
def test_create_server_missing_properties(
    client,
    vault_mock,
    db_session_mock,
    server_data,
    missing_property
):
    rv = client.post(
        f'{API_BASE}/satellite/server',
        headers={'Authorization': 'Bearer foobar'},
        json=server_data,
    )

    if missing_property != 'name':
        model.SatelliteServer.query.filter.return_value.count.return_value = 0

    vault_mock.write.assert_not_called()

    db_session_mock.add.assert_not_called()

    assert rv.status_code == 400, rv.data
    assert rv.json['title'] == 'Bad Request'
    assert rv.json['detail'] == f'\'{missing_property}\' is a required property'


@pytest.mark.parametrize('duplicate_property', ['name', 'hostname'])
def test_create_server_duplicate_properties(
    client,
    db_unique_violation,
    vault_mock,
    duplicate_property
):
    server_data = {
        'name': 'test',
        'owner_group_id': '00000000-0000-0000-0000-000000000000',
        'hostname': 'satellite.example.com',
        'insecure': True,
        'credentials': 'kv/test',
    }
    duplicate_value = server_data[duplicate_property]

    db_unique_violation(duplicate_property, duplicate_value)

    rv = client.post(
        f'{API_BASE}/satellite/server',
        headers={'Authorization': 'Bearer foobar'},
        json=server_data,
    )

    assert rv.status_code == 400, rv.data
    assert rv.json['title'] == 'Bad Request'
    assert rv.json['detail'] == (
        f'Key ({duplicate_property})=({duplicate_value}) already exists.'
    )

    vault_mock.write.assert_not_called()


def test_create_server_unauthorized(client, db_session_mock):
    server_data = {
        'name': 'test',
        'owner_group_id': '00000000-0000-0000-0000-000000000000',
        'hostname': 'satellite.example.com',
        'insecure': True,
        'credentials': 'kv/test',
    }

    rv = client.post(
        f'{API_BASE}/satellite/server',
        json=server_data,
    )

    db_session_mock.add.assert_not_called()

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_update_server(client, keycloak_mock):
    server = model.SatelliteServer(
        id=1,
        name='test',
        description='',
        owner_group_id='00000000-0000-0000-0000-000000000000',
        hostname='satellite.example.com',
        insecure=False,
        credentials='kv/test',
    )
    model.SatelliteServer.query.get.return_value = server

    keycloak_mock.group_get_name.return_value = 'test-group'

    model.SatelliteServer.query.filter.return_value.count.side_effect = [0, 0]

    rv = client.patch(
        f'{API_BASE}/satellite/server/1',
        headers={'Authorization': 'Bearer foobar'},
        json={
            'name': 'new',
            'description': 'new desc',
        },
    )

    assert rv.status_code == 200, rv.data

    model.SatelliteServer.query.get.assert_called_with(1)

    assert server.name == 'new'
    assert server.description == 'new desc'


@pytest.mark.parametrize('duplicate_property', ['name', 'hostname'])
def test_update_server_duplicate_properties(
    client,
    db_unique_violation,
    vault_mock,
    duplicate_property
):
    server = model.SatelliteServer(
        id=1,
        name='test',
        description='',
        owner_group_id='00000000-0000-0000-0000-000000000000',
        hostname='satellite.example.com',
        insecure=False,
        credentials='kv/test',
    )

    server_data = {
        'name': 'new-name',
        'hostname': 'new.example.com',
    }
    duplicate_value = server_data[duplicate_property]

    db_unique_violation(duplicate_property, duplicate_value)

    rv = client.patch(
        f'{API_BASE}/satellite/server/1',
        headers={'Authorization': 'Bearer foobar'},
        json=server_data,
    )

    assert rv.status_code == 400, rv.data
    assert rv.json['title'] == 'Bad Request'
    assert rv.json['detail'] == (
        f'Key ({duplicate_property})=({duplicate_value}) already exists.'
    )

    vault_mock.write.assert_not_called()


def test_update_server_unauthorized(client):
    rv = client.patch(
        f'{API_BASE}/satellite/server/1',
        json={
            'name': 'new',
            'description': 'new desc',
        },
    )

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_update_server_non_existent(client, vault_mock):
    server_id = 1

    model.SatelliteServer.query.get.return_value = None

    rv = client.patch(
        f'{API_BASE}/satellite/server/{server_id}',
        headers={'Authorization': 'Bearer foobar'},
        json={
            'name': 'new',
            'description': 'new desc',
        },
    )

    model.SatelliteServer.query.get.assert_called_with(server_id)

    assert rv.status_code == 404, rv.data
    assert rv.json['title'] == 'Not Found'
    assert rv.json['detail'] == f'Server {server_id} does not exist'

    vault_mock.write.assert_not_called()


def test_delete_server(client, db_session_mock, keycloak_mock):
    server = model.SatelliteServer(
        id=1,
        name='test',
        description='',
        owner_group_id='00000000-0000-0000-0000-000000000000',
        hostname='satellite.example.com',
        insecure=False,
        credentials='kv/test',
    )
    model.SatelliteServer.query.get.return_value = server

    keycloak_mock.group_get_name.return_value = 'test-group'

    rv = client.delete(
        f'{API_BASE}/satellite/server/1',
        headers={'Authorization': 'Bearer foobar'},
    )

    assert rv.status_code == 204, rv.data

    model.SatelliteServer.query.get.assert_called_with(1)
    db_session_mock.delete.assert_called_with(server)


def test_delete_server_unauthorized(client, db_session_mock):
    rv = client.delete(
        f'{API_BASE}/satellite/server/1',
    )

    db_session_mock.delete.assert_not_called()

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_delete_server_non_existent(client, db_session_mock):
    server_id = 1

    model.SatelliteServer.query.get.return_value = None

    rv = client.delete(
        f'{API_BASE}/satellite/server/{server_id}',
        headers={'Authorization': 'Bearer foobar'},
    )

    db_session_mock.delete.assert_not_called()

    assert rv.status_code == 404, rv.data
    assert rv.json['title'] == 'Not Found'
    assert rv.json['detail'] == f'Server {server_id} does not exist'
