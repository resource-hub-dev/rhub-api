import datetime
from contextlib import contextmanager
from unittest.mock import ANY

import pytest
from dateutil.tz import tzutc

from rhub.api.vault import Vault
from rhub.lab import model


API_BASE = '/v0'
AUTH_HEADER = {'Authorization': 'Basic X190b2tlbl9fOmR1bW15Cg=='}


def _db_add_row_side_effect(data_added):
    def side_effect(row):
        for k, v in data_added.items():
            setattr(row, k, v)
    return side_effect


def test_location_list(client):
    model.Location.query.limit.return_value.offset.return_value = [
        model.Location(
            id=1,
            name='RDU',
            description='',
        ),
    ]
    model.Location.query.count.return_value = 1

    rv = client.get(
        f'{API_BASE}/lab/location',
        headers=AUTH_HEADER,
    )

    assert rv.status_code == 200
    assert rv.json == {
        'data': [
            {
                'id': 1,
                'name': 'RDU',
                'description': '',
                '_href': ANY,
            }
        ],
        'total': 1,
    }


def test_location_list_unauthorized(client):
    rv = client.get(
        f'{API_BASE}/lab/location',
    )

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_location_get(client):
    model.Location.query.get.return_value = model.Location(
        id=1,
        name='RDU',
        description='',
    )

    rv = client.get(
        f'{API_BASE}/lab/location/1',
        headers=AUTH_HEADER,
    )

    model.Location.query.get.assert_called_with(1)

    assert rv.status_code == 200
    assert rv.json == {
        'id': 1,
        'name': 'RDU',
        'description': '',
        '_href': ANY,
    }


def test_location_get_unauthorized(client):
    location_id = 1

    rv = client.get(
        f'{API_BASE}/lab/location/{location_id}',
    )

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_location_get_non_existent(client):
    location_id = 1

    model.Location.query.get.return_value = None

    rv = client.get(
        f'{API_BASE}/lab/location/{location_id}',
        headers=AUTH_HEADER,
    )

    model.Location.query.get.assert_called_with(location_id)

    assert rv.status_code == 404, rv.data
    assert rv.json['title'] == 'Not Found'
    assert rv.json['detail'] == f'Location {location_id} does not exist'


def test_location_create(client, db_session_mock, mocker):
    location_data = {
        'name': 'RDU',
        'description': 'Raleigh',
    }

    model.Location.query.filter.return_value.count.return_value = 0
    db_session_mock.add.side_effect = _db_add_row_side_effect({'id': 1})

    rv = client.post(
        f'{API_BASE}/lab/location',
        headers=AUTH_HEADER,
        json=location_data,
    )

    db_session_mock.add.assert_called()

    location = db_session_mock.add.call_args.args[0]
    for k, v in location_data.items():
        assert getattr(location, k) == v

    assert rv.status_code == 200
    assert rv.json == {
        'id': 1,
        'name': 'RDU',
        'description': 'Raleigh',
        '_href': ANY,
    }


def test_location_create_unauthorized(client, db_session_mock):
    location_data = {
        'name': 'RDU',
        'description': 'Raleigh',
    }

    rv = client.post(
        f'{API_BASE}/lab/location',
        json=location_data,
    )

    db_session_mock.add.assert_not_called()

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_location_create_missing_name(client, db_session_mock):
    location_data = {
        'description': 'Raleigh',
    }

    rv = client.post(
        f'{API_BASE}/lab/location',
        headers=AUTH_HEADER,
        json=location_data,
    )

    db_session_mock.add.assert_not_called()

    assert rv.status_code == 400, rv.data
    assert rv.json['title'] == 'Bad Request'
    assert rv.json['detail'] == "'name' is a required property"


def test_location_create_duplicate_name(client, db_session_mock):
    location_data = {
        'name': 'RDU',
        'description': 'Raleigh',
    }

    model.Location.query.filter.return_value.count.return_value = 1

    rv = client.post(
        f'{API_BASE}/lab/location',
        headers=AUTH_HEADER,
        json=location_data,
    )

    db_session_mock.add.assert_not_called()

    assert rv.status_code == 400, rv.data
    assert rv.json['title'] == 'Bad Request'
    assert rv.json['detail'] == (
        f'Location with name {location_data["name"]!r} already exists'
    )


def test_location_update(client):
    location = model.Location(
        id=1,
        name='RDU',
        description='',
    )
    model.Location.query.get.return_value = location

    rv = client.patch(
        f'{API_BASE}/lab/location/1',
        headers=AUTH_HEADER,
        json={
            'description': 'Raleigh',
        },
    )

    model.Location.query.get.assert_called_with(1)

    assert location.description == 'Raleigh'

    assert rv.status_code == 200
    assert rv.json == {
        'id': 1,
        'name': 'RDU',
        'description': 'Raleigh',
        '_href': ANY,
    }


def test_location_update_unauthorized(client, db_session_mock):
    rv = client.patch(
        f'{API_BASE}/lab/location/1',
        json={
            'description': 'Raleigh',
        },
    )

    db_session_mock.commit.assert_not_called()

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_location_update_non_existent(client, db_session_mock):
    location_id = 1
    
    model.Location.query.get.return_value = None

    rv = client.patch(
        f'{API_BASE}/lab/location/{location_id}',
        headers=AUTH_HEADER,
        json={
            'description': 'Raleigh',
        },
    )

    model.Location.query.get.assert_called_with(location_id)
    db_session_mock.commit.assert_not_called()

    assert rv.status_code == 404, rv.data
    assert rv.json['title'] == 'Not Found'
    assert rv.json['detail'] == f'Location {location_id} does not exist'


def test_location_update_duplicate_name(client, db_unique_violation):
    location = model.Location(
        id=1,
        name='RDU',
        description='',
    )
    model.Location.query.get.return_value = location

    new_data = {'name': 'PNQ'}

    db_unique_violation('name', new_data['name'])

    rv = client.patch(
        f'{API_BASE}/lab/location/{location.id}',
        headers=AUTH_HEADER,
        json=new_data,
    )

    assert rv.status_code == 400, rv.data
    assert rv.json['title'] == 'Bad Request'
    assert rv.json['detail'] == (
        f'Key (name)=({new_data["name"]}) already exists.'
    )


def test_location_delete(client, db_session_mock):
    location = model.Location(
        id=1,
        name='RDU',
        description='',
    )
    model.Location.query.get.return_value = location

    rv = client.delete(
        f'{API_BASE}/lab/location/1',
        headers=AUTH_HEADER,
    )

    model.Location.query.get.assert_called_with(1)
    db_session_mock.delete.assert_called_with(location)

    assert rv.status_code == 204


def test_location_delete_unatuhorized(client, db_session_mock):
    rv = client.delete(
        f'{API_BASE}/lab/location/1',
    )

    db_session_mock.delete.assert_not_called()

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_location_delete_non_existent(client, db_session_mock):
    location_id = 1

    model.Location.query.get.return_value = None

    rv = client.delete(
        f'{API_BASE}/lab/location/{location_id}',
        headers=AUTH_HEADER,
    )

    model.Location.query.get.assert_called_with(location_id)
    db_session_mock.delete.assert_not_called()

    assert rv.status_code == 404, rv.data
    assert rv.json['title'] == 'Not Found'
    assert rv.json['detail'] == f'Location {location_id} does not exist'
