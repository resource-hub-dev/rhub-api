import datetime

import pytest
from dateutil.tz import tzutc

from rhub.lab import model
from rhub.api.vault import Vault
from rhub.auth.keycloak import KeycloakClient


API_BASE = '/v0'


@pytest.fixture(autouse=True)
def date_now_mock(mocker):
    date_now_mock = mocker.patch('rhub.api.lab.cluster.date_now')
    date_now_mock.return_value = datetime.datetime(2021, 1, 1, 1, 0, 0, tzinfo=tzutc())
    yield date_now_mock


def _db_add_row_side_effect(data_added):
    def side_effect(row):
        for k, v in data_added.items():
            setattr(row, k, v)
    return side_effect


def test_list_products(client):
    model.Product.query.limit.return_value.offset.return_value = [
        model.Product(
            id=1,
            name='dummy',
            description='dummy',
            enabled=True,
            tower_template_name='dummy',
            parameters=[],
        ),
    ]
    model.Product.query.count.return_value = 1

    rv = client.get(
        f'{API_BASE}/lab/product',
        headers={'Authorization': 'Bearer foobar'},
    )

    assert rv.status_code == 200
    assert rv.json == {
        'data': [
            {
                'id': 1,
                'name': 'dummy',
                'description': 'dummy',
                'enabled': True,
                'tower_template_name': 'dummy',
                'parameters': [],
            },
        ],
        'total': 1,
    }


def test_get_product(client):
    model.Product.query.get.return_value = model.Product(
        id=1,
        name='dummy',
        description='dummy',
        enabled=True,
        tower_template_name='dummy',
        parameters=[],
    )

    rv = client.get(
        f'{API_BASE}/lab/product/1',
        headers={'Authorization': 'Bearer foobar'},
    )

    assert rv.status_code == 200
    assert rv.json == {
        'id': 1,
        'name': 'dummy',
        'description': 'dummy',
        'enabled': True,
        'tower_template_name': 'dummy',
        'parameters': [],
    }


def test_create_product(client, db_session_mock):
    product_data = {
        'name': 'dummy',
        'description': 'dummy',
        'enabled': True,
        'tower_template_name': 'dummy',
        'parameters': [],
    }

    model.Product.query.filter.return_value.count.return_value = 0
    db_session_mock.add.side_effect = _db_add_row_side_effect({'id': 1})

    rv = client.post(
        f'{API_BASE}/lab/product',
        headers={'Authorization': 'Bearer foobar'},
        json=product_data,
    )

    assert rv.status_code == 200

    db_session_mock.add.assert_called()
    db_session_mock.commit.assert_called()

    product = db_session_mock.add.call_args.args[0]
    for k, v in product_data.items():
        assert getattr(product, k) == v


def test_update_product(client, db_session_mock):
    product = model.Product(
        id=1,
        name='dummy',
        description='dummy',
        enabled=True,
        tower_template_name='dummy',
        parameters=[],
    )
    model.Product.query.get.return_value = product

    rv = client.patch(
        f'{API_BASE}/lab/product/1',
        headers={'Authorization': 'Bearer foobar'},
        json={
            'name': 'name change',
            'description': 'desc change',
        },
    )

    assert rv.status_code == 200

    db_session_mock.commit.assert_called()

    assert product.name == 'name change'
    assert product.description == 'desc change'


def test_delete_product(client, db_session_mock):
    product = model.Product(
        id=1,
        name='dummy',
        description='dummy',
        enabled=True,
        tower_template_name='dummy',
        parameters=[],
    )
    model.Product.query.get.return_value = product
    model.RegionProduct.query.filter.return_value.count.return_value = 0

    rv = client.delete(
        f'{API_BASE}/lab/product/1',
        headers={'Authorization': 'Bearer foobar'},
    )

    assert rv.status_code == 204

    db_session_mock.delete.assert_called_with(product)
    db_session_mock.commit.assert_called()
