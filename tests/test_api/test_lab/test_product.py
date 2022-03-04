import datetime
from unittest.mock import ANY
from contextlib import contextmanager

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
            tower_template_name_create='dummy',
            tower_template_name_delete='dummy',
            parameters=[],
            flavors={},
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
                'tower_template_name_create': 'dummy',
                'tower_template_name_delete': 'dummy',
                'parameters': [],
                'flavors': {},
                '_href': ANY,
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
        tower_template_name_create='dummy',
        tower_template_name_delete='dummy',
        parameters=[],
        flavors={},
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
        'tower_template_name_create': 'dummy',
        'tower_template_name_delete': 'dummy',
        'parameters': [],
        'flavors': {},
        '_href': ANY,
    }


def test_create_product(client, db_session_mock):
    product_data = {
        'name': 'dummy',
        'description': 'dummy',
        'enabled': True,
        'tower_template_name_create': 'dummy',
        'tower_template_name_delete': 'dummy',
        'parameters': [],
        'flavors': {},
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
        tower_template_name_create='dummy',
        tower_template_name_delete='dummy',
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
        tower_template_name_create='dummy',
        tower_template_name_delete='dummy',
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


@contextmanager
def does_not_raise():
    yield


def gen_validation_test_params(name, param_spec, params_vals_and_expectation):
    return [
        pytest.param(param_spec, param_vals, expectation, id=f'{name} {param_vals!r}')
        for param_vals, expectation in params_vals_and_expectation
    ]


@pytest.mark.parametrize(
    'param_spec, param_vals, expectation',
    [
        *gen_validation_test_params(
            'integer',
            {
                'variable': 'x',
                'type': 'integer',
            },
            [
                ({'x': 1}, does_not_raise()),
                ({'x': 'a'}, pytest.raises(ValueError)),
                # True == 1 and isinstance(True, int) are true in Py
                # but we should allow only int
                ({'x': True}, pytest.raises(ValueError)),
            ],
        ),
        *gen_validation_test_params(
            'integer min-max',
            {
                'variable': 'x',
                'type': 'integer',
                'min': 0,
                'max': 10,
            },
            [
                ({'x': 1}, does_not_raise()),
                ({'x': 100}, pytest.raises(ValueError)),
                ({'x': -10}, pytest.raises(ValueError))
            ],
        ),
        *gen_validation_test_params(
            'integer enum',
            {
                'variable': 'x',
                'type': 'integer',
                'enum': [2, 4, 8],
            },
            [
                ({'x': 2}, does_not_raise()),
                ({'x': 6}, pytest.raises(ValueError)),
            ],
        ),
        *gen_validation_test_params(
            'string',
            {
                'variable': 'x',
                'type': 'string',
            },
            [
                ({'x': 'a'}, does_not_raise()),
                ({'x': 1}, pytest.raises(ValueError)),
                ({'x': True}, pytest.raises(ValueError)),
            ],
        ),
        *gen_validation_test_params(
            'string mix-max len',
            {
                'variable': 'x',
                'type': 'string',
                'minLength': 2,
                'maxLength': 4,
            },
            [
                ({'x': 'abc'}, does_not_raise()),
                ({'x': ''}, pytest.raises(ValueError)),
                ({'x': '01234567'}, pytest.raises(ValueError))
            ],
        ),
        *gen_validation_test_params(
            'string enum',
            {
                'variable': 'x',
                'type': 'string',
                'enum': ['foo', 'bar'],
            },
            [
                ({'x': 'foo'}, does_not_raise()),
                ({'x': 'abc'}, pytest.raises(ValueError)),
            ],
        ),
        *gen_validation_test_params(
            'boolean',
            {
                'variable': 'x',
                'type': 'boolean',
            },
            [
                ({'x': True}, does_not_raise()),
                ({'x': False}, does_not_raise()),
                ({'x': 1}, pytest.raises(ValueError)),
                ({'x': 'yes'}, pytest.raises(ValueError)),
                ({'x': 'true'}, pytest.raises(ValueError)),
                ({'x': None}, pytest.raises(ValueError)),
            ],
        ),
        *gen_validation_test_params(
            'required',
            {
                'variable': 'x',
                'type': 'string',
                'required': False,
            },
            [
                ({}, does_not_raise()),
                ({'foo': 'bar'}, pytest.raises(ValueError)), # 'foo' is not in spec
                ({'x': 1}, pytest.raises(ValueError)),  # invalid type
            ],
        )
    ]
)
def test_product_params_validation(param_spec, param_vals, expectation):
    product = model.Product(
        id=1,
        name='dummy',
        description='dummy',
        enabled=True,
        tower_template_name_create='dummy',
        tower_template_name_delete='dummy',
        parameters=[param_spec],
    )

    with expectation:
        product.validate_cluster_params(param_vals)
