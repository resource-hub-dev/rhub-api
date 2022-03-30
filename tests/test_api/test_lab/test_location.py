import datetime
from unittest.mock import ANY
from contextlib import contextmanager

import pytest
from dateutil.tz import tzutc

from rhub.lab import model
from rhub.api.vault import Vault
from rhub.auth.keycloak import KeycloakClient


API_BASE = '/v0'


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
        headers={'Authorization': 'Bearer foobar'},
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


def test_location_get(client):
    model.Location.query.get.return_value = model.Location(
        id=1,
        name='RDU',
        description='',
    )

    rv = client.get(
        f'{API_BASE}/lab/location/1',
        headers={'Authorization': 'Bearer foobar'},
    )

    model.Location.query.get.assert_called_with(1)

    assert rv.status_code == 200
    assert rv.json == {
        'id': 1,
        'name': 'RDU',
        'description': '',
        '_href': ANY,
    }


def test_location_create(client, db_session_mock, mocker):
    location_data = {
        'name': 'RDU',
        'description': 'Raleigh',
    }

    model.Location.query.filter.return_value.count.return_value = 0
    db_session_mock.add.side_effect = _db_add_row_side_effect({'id': 1})

    rv = client.post(
        f'{API_BASE}/lab/location',
        headers={'Authorization': 'Bearer foobar'},
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


def test_location_update(client):
    location = model.Location(
        id=1,
        name='RDU',
        description='',
    )
    model.Location.query.get.return_value = location

    rv = client.patch(
        f'{API_BASE}/lab/location/1',
        headers={'Authorization': 'Bearer foobar'},
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


def test_location_delete(client, db_session_mock):
    location = model.Location(
        id=1,
        name='RDU',
        description='',
    )
    model.Location.query.get.return_value = location

    rv = client.delete(
        f'{API_BASE}/lab/location/1',
        headers={'Authorization': 'Bearer foobar'},
    )

    model.Location.query.get.assert_called_with(1)
    db_session_mock.delete.assert_called_with(location)

    assert rv.status_code == 204
