import base64
from unittest.mock import ANY

import pytest
import sqlalchemy.exc

from rhub.api.lab.region import VAULT_PATH_PREFIX
from rhub.api.vault import Vault
from rhub.auth.keycloak import KeycloakClient
from rhub.lab import model
from rhub.openstack import model as openstack_model


API_BASE = '/v0'


def _db_add_row_side_effect(data_added):
    def side_effect(row):
        for k, v in data_added.items():
            setattr(row, k, v)
    return side_effect


def test_to_dict(keycloak_mock):
    location = model.Location(
        id=1,
        name='RDU',
        description='Raleigh',
    )
    openstack = openstack_model.Cloud(
        id=1,
        name='test',
        description='',
        owner_group_id='00000000-0000-0000-0000-000000000000',
        url='https://openstack.example.com:13000',
        credentials='kv/test',
        domain_name='Default',
        domain_id='default',
        networks=['test_net'],
    )
    region = model.Region(
        id=1,
        name='test',
        location_id=location.id,
        location=location,
        description='desc',
        banner='ban',
        enabled=True,
        user_quota_id=1,
        user_quota=model.Quota(
            num_vcpus=40,
            ram_mb=200000,
            num_volumes=40,
            volumes_gb=540,
        ),
        total_quota_id=None,
        total_quota=None,
        lifespan_length=None,
        reservations_enabled=True,
        reservation_expiration_max=7,
        owner_group_id='00000000-0000-0000-0000-000000000000',
        users_group_id=None,
        tower_id=1,
        openstack_id=openstack.id,
        openstack=openstack,
        satellite_id=None,
        satellite=None,
    )

    keycloak_mock.group_get.return_value = {'name': 'foobar-group'}

    assert region.to_dict() == {
        'id': 1,
        'name': 'test',
        'location_id': 1,
        'location': {
            'id': 1,
            'name': 'RDU',
            'description': 'Raleigh',
        },
        'description': 'desc',
        'banner':'ban',
        'enabled': True,
        'user_quota': {
            'num_vcpus': 40,
            'ram_mb': 200000,
            'num_volumes': 40,
            'volumes_gb': 540,
        },
        'total_quota': None,
        'lifespan_length': None,
        'reservations_enabled': True,
        'reservation_expiration_max': 7,
        'owner_group_id': '00000000-0000-0000-0000-000000000000',
        'owner_group_name': 'foobar-group',
        'users_group_id': None,
        'users_group_name': None,
        'tower_id': 1,
        'openstack_id': 1,
        'openstack': {
            'id': 1,
            'name': 'test',
            'description': '',
            'owner_group_id': '00000000-0000-0000-0000-000000000000',
            'owner_group_name': 'foobar-group',
            'url': 'https://openstack.example.com:13000',
            'credentials': 'kv/test',
            'domain_name': 'Default',
            'domain_id': 'default',
            'networks': ['test_net'],
        },
        'satellite_id': None,
        'satellite': None,
    }


def test_list_regions(client, keycloak_mock):
    model.Region.query.limit.return_value.offset.return_value = [
        model.Region(
            id=1,
            name='test',
            location_id=1,
            location=model.Location(
                id=1,
                name='RDU',
                description='Raleigh',
            ),
            description='',
            banner='',
            enabled=True,
            user_quota_id=None,
            total_quota_id=None,
            lifespan_length=None,
            reservations_enabled=True,
            reservation_expiration_max=7,
            owner_group_id='00000000-0000-0000-0000-000000000000',
            users_group_id=None,
            tower_id=1,
            openstack_id=1,
            openstack=openstack_model.Cloud(
                id=1,
                name='test',
                description='',
                owner_group_id='00000000-0000-0000-0000-000000000000',
                url='https://openstack.example.com:13000',
                credentials='kv/test',
                domain_name='Default',
                domain_id='default',
                networks=['test_net'],
            ),
            satellite_id=None,
            satellite=None,
        ),
    ]
    model.Region.query.count.return_value = 1

    keycloak_mock.group_get.return_value = {'name': 'foobar-group'}

    rv = client.get(
        f'{API_BASE}/lab/region',
        headers={'Authorization': 'Bearer foobar'},
    )

    assert rv.status_code == 200, rv.data
    assert rv.json == {
        'data': [
            {
                'id': 1,
                'name': 'test',
                'location_id': 1,
                'location': {
                    'id': 1,
                    'name': 'RDU',
                    'description': 'Raleigh',
                },
                'description': '',
                'banner': '',
                'enabled': True,
                'user_quota': None,
                'total_quota': None,
                'lifespan_length': None,
                'reservations_enabled': True,
                'reservation_expiration_max': 7,
                'owner_group_id': '00000000-0000-0000-0000-000000000000',
                'owner_group_name': 'foobar-group',
                'users_group_id': None,
                'users_group_name': None,
                'tower_id': 1,
                'openstack_id': 1,
                'openstack': {
                    'id': 1,
                    'name': 'test',
                    'description': '',
                    'owner_group_id': '00000000-0000-0000-0000-000000000000',
                    'owner_group_name': 'foobar-group',
                    'url': 'https://openstack.example.com:13000',
                    'credentials': 'kv/test',
                    'domain_name': 'Default',
                    'domain_id': 'default',
                    'networks': ['test_net'],
                },
                'satellite_id': None,
                'satellite': None,
                '_href': ANY,
            },
        ],
        'total': 1,
    }


def test_get_region(client, keycloak_mock):
    model.Region.query.get.return_value = model.Region(
        id=1,
        name='test',
        location_id=1,
        location=model.Location(
            id=1,
            name='RDU',
            description='Raleigh',
        ),
        description='',
        banner='',
        enabled=True,
        user_quota_id=None,
        total_quota_id=None,
        lifespan_length=None,
        reservations_enabled=True,
        reservation_expiration_max=7,
        owner_group_id='00000000-0000-0000-0000-000000000000',
        users_group_id=None,
        tower_id=1,
        openstack_id=1,
        openstack=openstack_model.Cloud(
            id=1,
            name='test',
            description='',
            owner_group_id='00000000-0000-0000-0000-000000000000',
            url='https://openstack.example.com:13000',
            credentials='kv/test',
            domain_name='Default',
            domain_id='default',
            networks=['test_net'],
        ),
        satellite_id=None,
        satellite=None,
    )

    keycloak_mock.group_get.return_value = {'name': 'foobar-group'}

    rv = client.get(
        f'{API_BASE}/lab/region/1',
        headers={'Authorization': 'Bearer foobar'},
    )

    assert rv.status_code == 200, rv.data

    model.Region.query.get.assert_called_with(1)

    assert rv.json == {
        'id': 1,
        'name': 'test',
        'location_id': 1,
        'location': {
            'id': 1,
            'name': 'RDU',
            'description': 'Raleigh',
        },
        'description': '',
        'banner': '',
        'enabled': True,
        'user_quota': None,
        'total_quota': None,
        'lifespan_length': None,
        'reservations_enabled': True,
        'reservation_expiration_max': 7,
        'owner_group_id': '00000000-0000-0000-0000-000000000000',
        'owner_group_name': 'foobar-group',
        'users_group_id': None,
        'users_group_name': None,
        'tower_id': 1,
        'openstack_id': 1,
        'openstack': {
            'id': 1,
            'name': 'test',
            'description': '',
            'owner_group_id': '00000000-0000-0000-0000-000000000000',
            'owner_group_name': 'foobar-group',
            'url': 'https://openstack.example.com:13000',
            'credentials': 'kv/test',
            'domain_name': 'Default',
            'domain_id': 'default',
            'networks': ['test_net'],
        },
        'satellite_id': None,
        'satellite': None,
        '_href': ANY,
    }


def test_create_region(client, db_session_mock, keycloak_mock, mocker):
    group_id = '10000000-2000-3000-4000-000000000000'
    region_data = {
        'name': 'test',
        'location_id': 1,
        'tower_id': 1,
        'openstack_id': 1,
        'owner_group_id': group_id,
    }

    model.Region.query.filter.return_value.count.return_value = 0
    db_session_mock.add.side_effect = _db_add_row_side_effect({'id': 1})

    keycloak_mock.group_get.return_value = {'name': 'foobar-group'}

    rv = client.post(
        f'{API_BASE}/lab/region',
        headers={'Authorization': 'Bearer foobar'},
        json=region_data,
    )

    assert rv.status_code == 200, rv.data

    db_session_mock.add.assert_called()

    region = db_session_mock.add.call_args.args[0]
    for k, v in region_data.items():
        if isinstance(v, dict):
            for k2, v2 in v.items():
                assert getattr(region, f'{k}_{k2}') == v2
        else:
            assert getattr(region, k) == v

    assert rv.json['user_quota'] is None
    assert rv.json['owner_group_id'] == group_id
    assert rv.json['users_group_id'] is None


def test_create_region_with_quota(client, db_session_mock, keycloak_mock, mocker):
    group_id = '10000000-2000-3000-4000-000000000000'
    quota_data = {
        'num_vcpus': 40,
        'ram_mb': 200000,
        'num_volumes': 40,
        'volumes_gb': 540,
    }
    region_data = {
        'name': 'test',
        'location_id': 1,
        'tower_id': 1,
        'user_quota': quota_data,
        'total_quota': None,
        'owner_group_id': group_id,
        'openstack_id': 1,
    }

    model.Region.query.filter.return_value.count.return_value = 0
    db_session_mock.add.side_effect = _db_add_row_side_effect({'id': 1})

    keycloak_mock.group_get.return_value = {'name': 'foobar-group'}

    rv = client.post(
        f'{API_BASE}/lab/region',
        headers={'Authorization': 'Bearer foobar'},
        json=region_data,
    )

    assert rv.status_code == 200, rv.data

    db_session_mock.add.assert_called()

    region = db_session_mock.add.call_args.args[0]
    for k, v in region_data.items():
        if k in ['user_quota', 'total_quota']:
            continue
        if isinstance(v, dict):
            for k2, v2 in v.items():
                assert getattr(region, f'{k}_{k2}') == v2
        else:
            assert getattr(region, k) == v

    assert region.user_quota is not None
    for k, v in quota_data.items():
        assert getattr(region.user_quota, k) == v

    assert rv.json['user_quota'] == quota_data
    assert rv.json['owner_group_id'] == group_id
    assert rv.json['users_group_id'] is None


def test_update_region(client):
    region = model.Region(
        id=1,
        name='test',
        location_id=1,
        location=model.Location(
            id=1,
            name='RDU',
            description='Raleigh',
        ),
        description='',
        banner='',
        enabled=True,
        user_quota_id=None,
        total_quota_id=None,
        lifespan_length=None,
        reservations_enabled=True,
        reservation_expiration_max=7,
        owner_group_id='00000000-0000-0000-0000-000000000000',
        users_group_id=None,
        tower_id=1,
        openstack_id=1,
        openstack=openstack_model.Cloud(
            id=1,
            name='test',
            description='',
            owner_group_id='00000000-0000-0000-0000-000000000000',
            url='https://openstack.example.com:13000',
            credentials='kv/test',
            domain_name='Default',
            domain_id='default',
            networks=['test_net'],
        ),
        satellite_id=None,
        satellite=None,
    )
    model.Region.query.get.return_value = region

    rv = client.patch(
        f'{API_BASE}/lab/region/1',
        headers={'Authorization': 'Bearer foobar'},
        json={
            'name': 'new',
            'description': 'new desc',
        },
    )

    assert rv.status_code == 200, rv.data

    model.Region.query.get.assert_called_with(1)

    assert region.name == 'new'
    assert region.description == 'new desc'


@pytest.mark.parametrize(
    'quota_data',
    [
        pytest.param(
            {
                'num_vcpus': 40,
                'ram_mb': 200000,
                'num_volumes': 40,
                'volumes_gb': 540,
            },
            id='quota enable',
        ),
        pytest.param(
            None,
            id='quota disable',
        ),
    ]
)
def test_update_region_quota(client, keycloak_mock, quota_data):
    region = model.Region(
        id=1,
        name='test',
        location_id=1,
        location=model.Location(
            id=1,
            name='RDU',
            description='Raleigh',
        ),
        description='',
        banner='',
        enabled=True,
        user_quota_id=None,
        total_quota_id=None,
        lifespan_length=None,
        reservations_enabled=True,
        reservation_expiration_max=7,
        owner_group_id='00000000-0000-0000-0000-000000000000',
        users_group_id=None,
        tower_id=1,
        openstack_id=1,
        openstack=openstack_model.Cloud(
            id=1,
            name='test',
            description='',
            owner_group_id='00000000-0000-0000-0000-000000000000',
            url='https://openstack.example.com:13000',
            credentials='kv/test',
            domain_name='Default',
            domain_id='default',
            networks=['test_net'],
        ),
        satellite_id=None,
        satellite=None,
    )
    model.Region.query.get.return_value = region

    rv = client.patch(
        f'{API_BASE}/lab/region/1',
        headers={'Authorization': 'Bearer foobar'},
        json={'user_quota': quota_data},
    )

    assert rv.status_code == 200, rv.data

    model.Region.query.get.assert_called_with(1)

    assert rv.json['user_quota'] == quota_data


def test_delete_region(client, db_session_mock):
    group_id = '00000000-0000-0000-0000-000000000000'
    region = model.Region(
        id=1,
        name='test',
        location_id=1,
        location=model.Location(
            id=1,
            name='RDU',
            description='Raleigh',
        ),
        description='',
        banner='',
        enabled=True,
        user_quota_id=None,
        total_quota_id=None,
        lifespan_length=None,
        reservations_enabled=True,
        reservation_expiration_max=7,
        owner_group_id=group_id,
        users_group_id=None,
        tower_id=1,
        openstack_id=1,
        openstack=openstack_model.Cloud(
            id=1,
            name='test',
            description='',
            owner_group_id='00000000-0000-0000-0000-000000000000',
            url='https://openstack.example.com:13000',
            credentials='kv/test',
            domain_name='Default',
            domain_id='default',
            networks=['test_net'],
        ),
        satellite_id=None,
        satellite=None,
    )
    model.Region.query.get.return_value = region
    model.RegionProduct.query.filter.return_value.count.return_value = 0

    rv = client.delete(
        f'{API_BASE}/lab/region/1',
        headers={'Authorization': 'Bearer foobar'},
    )

    assert rv.status_code == 204, rv.data

    model.Region.query.get.assert_called_with(1)
    db_session_mock.delete.assert_called_with(region)


def test_region_list_products(client):
    products_relation = [
        model.RegionProduct(
            region_id=1,
            product_id=1,
            product=model.Product(
                id=1,
                name='dummy',
                description='dummy',
                enabled=True,
                tower_template_name_create='dummy',
                tower_template_name_delete='dummy',
                parameters=[],
                flavors={},
            ),
            enabled=True,
        ),
    ]

    model.Region.query.get.return_value = model.Region(
        id=1,
        name='test',
        location_id=1,
        location=model.Location(
            id=1,
            name='RDU',
            description='Raleigh',
        ),
        description='',
        banner='',
        enabled=True,
        user_quota_id=None,
        total_quota_id=None,
        lifespan_length=None,
        reservations_enabled=True,
        reservation_expiration_max=7,
        owner_group_id='00000000-0000-0000-0000-000000000000',
        users_group_id=None,
        tower_id=1,
        openstack_id=1,
        openstack=openstack_model.Cloud(
            id=1,
            name='test',
            description='',
            owner_group_id='00000000-0000-0000-0000-000000000000',
            url='https://openstack.example.com:13000',
            credentials='kv/test',
            domain_name='Default',
            domain_id='default',
            networks=['test_net'],
        ),
        satellite_id=None,
        satellite=None,
        products_relation=products_relation
    )

    rv = client.get(
        f'{API_BASE}/lab/region/1/products',
        headers={'Authorization': 'Bearer foobar'},
    )

    assert rv.status_code == 200, rv.data
    assert rv.json == [
        {
            'region_id': 1,
            'product_id': 1,
            'product': {
                'id': 1,
                'name': 'dummy',
                'description': 'dummy',
                'enabled': True,
                'tower_template_name_create': 'dummy',
                'tower_template_name_delete': 'dummy',
                'parameters': [],
                'flavors': {},
            },
            'enabled': True,
            '_href': ANY,
        },
    ]


def test_region_add_product(client, db_session_mock):
    model.Region.query.get.return_value = model.Region(
        id=1,
        name='test',
        location_id=1,
        location=model.Location(
            id=1,
            name='RDU',
            description='Raleigh',
        ),
        description='',
        banner='',
        enabled=True,
        user_quota_id=None,
        total_quota_id=None,
        lifespan_length=None,
        reservations_enabled=True,
        reservation_expiration_max=7,
        owner_group_id='00000000-0000-0000-0000-000000000000',
        users_group_id=None,
        tower_id=1,
        openstack_id=1,
        openstack=openstack_model.Cloud(
            id=1,
            name='test',
            description='',
            owner_group_id='00000000-0000-0000-0000-000000000000',
            url='https://openstack.example.com:13000',
            credentials='kv/test',
            domain_name='Default',
            domain_id='default',
            networks=['test_net'],
        ),
        satellite_id=None,
        satellite=None,
        products_relation=[],
    )

    model.Product.query.get.return_value = model.Product(
        id=10,
        name='dummy',
        description='dummy',
        tower_template_name_create='dummy',
        tower_template_name_delete='dummy',
        parameters=[],
    )

    model.RegionProduct.query.filter.return_value.count.return_value = 0

    rv = client.post(
        f'{API_BASE}/lab/region/1/products',
        headers={'Authorization': 'Bearer foobar'},
        json={'id': 10},
    )

    assert rv.status_code == 204, rv.data

    db_session_mock.add.assert_called()
    db_session_mock.commit.assert_called()

    region_product = db_session_mock.add.call_args.args[0]
    assert region_product.region_id == 1
    assert region_product.product_id == 10
    assert region_product.enabled is True


def test_region_disable_product(client, db_session_mock):
    model.Region.query.get.return_value = model.Region(
        id=1,
        name='test',
        location_id=1,
        location=model.Location(
            id=1,
            name='RDU',
            description='Raleigh',
        ),
        description='',
        banner='',
        enabled=True,
        user_quota_id=None,
        total_quota_id=None,
        lifespan_length=None,
        reservations_enabled=True,
        reservation_expiration_max=7,
        owner_group_id='00000000-0000-0000-0000-000000000000',
        users_group_id=None,
        tower_id=1,
        openstack_id=1,
        openstack=openstack_model.Cloud(
            id=1,
            name='test',
            description='',
            owner_group_id='00000000-0000-0000-0000-000000000000',
            url='https://openstack.example.com:13000',
            credentials='kv/test',
            domain_name='Default',
            domain_id='default',
            networks=['test_net'],
        ),
        satellite_id=None,
        satellite=None,
        products_relation=[],
    )

    model.Product.query.get.return_value = model.Product(
        id=10,
        name='dummy',
        description='dummy',
        tower_template_name_create='dummy',
        tower_template_name_delete='dummy',
        parameters=[],
    )

    region_product = model.RegionProduct(region_id=1, product_id=10, enabled=True)

    model.RegionProduct.query.filter.return_value.count.return_value = 1
    model.RegionProduct.query.filter.return_value.all.return_value = [region_product]

    rv = client.post(
        f'{API_BASE}/lab/region/1/products',
        headers={'Authorization': 'Bearer foobar'},
        json={'id': 10, 'enabled': False},
    )

    assert rv.status_code == 204, rv.data

    db_session_mock.commit.assert_called()

    assert region_product.enabled is False


def test_region_delete_product(client, db_session_mock):
    model.Region.query.get.return_value = model.Region(
        id=1,
        name='test',
        location_id=1,
        location=model.Location(
            id=1,
            name='RDU',
            description='Raleigh',
        ),
        description='',
        banner='',
        enabled=True,
        user_quota_id=None,
        total_quota_id=None,
        lifespan_length=None,
        reservations_enabled=True,
        reservation_expiration_max=7,
        owner_group_id='00000000-0000-0000-0000-000000000000',
        users_group_id=None,
        tower_id=1,
        openstack_id=1,
        openstack=openstack_model.Cloud(
            id=1,
            name='test',
            description='',
            owner_group_id='00000000-0000-0000-0000-000000000000',
            url='https://openstack.example.com:13000',
            credentials='kv/test',
            domain_name='Default',
            domain_id='default',
            networks=['test_net'],
        ),
        satellite_id=None,
        satellite=None,
        products_relation=[],
    )

    model.Product.query.get.return_value = model.Product(
        id=10,
        name='dummy',
        description='dummy',
        tower_template_name_create='dummy',
        tower_template_name_delete='dummy',
        parameters=[],
    )

    region_product = model.RegionProduct(region_id=1, product_id=10)

    model.RegionProduct.query.filter.return_value.count.return_value = 1
    model.RegionProduct.query.filter.return_value.all.return_value = [region_product]

    rv = client.delete(
        f'{API_BASE}/lab/region/1/products',
        headers={'Authorization': 'Bearer foobar'},
        json={'id': 10},
    )

    assert rv.status_code == 204, rv.data

    db_session_mock.delete.assert_called_with(region_product)
    db_session_mock.commit.assert_called()
