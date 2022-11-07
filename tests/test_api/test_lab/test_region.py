import base64
from unittest.mock import ANY

import pytest
import sqlalchemy.exc

from rhub.api.vault import Vault
from rhub.auth.keycloak import KeycloakClient
from rhub.lab import model
from rhub.openstack import model as openstack_model

from rhub.auth.keycloak import KeycloakGetError


API_BASE = '/v0'
AUTH_HEADER = {'Authorization': 'Basic X190b2tlbl9fOmR1bW15Cg=='}


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
        dns_id=None,
        dns=None,
    )

    keycloak_mock.group_get_name.return_value = 'foobar-group'

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
        'dns_id': None,
        'dns': None,
    }


def test_list_regions(client, keycloak_mock):
    model.Region.query.outerjoin.return_value.limit.return_value.offset.return_value = [
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
            dns_id=None,
            dns=None,
        ),
    ]
    model.Region.query.outerjoin.return_value.count.return_value = 1

    keycloak_mock.group_get_name.return_value = 'foobar-group'

    rv = client.get(
        f'{API_BASE}/lab/region',
        headers=AUTH_HEADER,
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
                'dns_id': None,
                'dns': None,
                '_href': ANY,
            },
        ],
        'total': 1,
    }


def test_list_regions_unauthorized(client):
    rv = client.get(
        f'{API_BASE}/lab/region',
    )

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_query_regions(client):
    # Simple test to detect issues with deepObject query parameters,
    # https://github.com/resource-hub-dev/rhub-api/pull/150
    q = model.Region.query.outerjoin.return_value.filter.return_value
    q.limit.return_value.offset.return_value = []
    q.count.return_value = 0

    rv = client.get(
        f'{API_BASE}/lab/region',
        query_string={'filter[name]': 'test'},
        headers=AUTH_HEADER,
    )

    assert rv.status_code == 200, rv.data
    assert rv.json == {'data': [], 'total': 0}


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
        dns_id=None,
        dns=None,
    )

    keycloak_mock.group_get_name.return_value = 'foobar-group'

    rv = client.get(
        f'{API_BASE}/lab/region/1',
        headers=AUTH_HEADER,
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
        'dns_id': None,
        'dns': None,
        '_href': ANY,
    }


def test_get_region_unauthorized(client):
    rv = client.get(
        f'{API_BASE}/lab/region/1',
    )

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_get_region_non_existent(client):
    region_id = 1
    
    model.Region.query.get.return_value = None

    rv = client.get(
        f'{API_BASE}/lab/region/{region_id}',
        headers=AUTH_HEADER,
    )

    model.Region.query.get.assert_called_with(region_id)

    assert rv.status_code == 404, rv.data
    assert rv.json['title'] == 'Not Found'
    assert rv.json['detail'] == f'Region {region_id} does not exist'


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

    keycloak_mock.group_get_name.return_value = 'foobar-group'

    rv = client.post(
        f'{API_BASE}/lab/region',
        headers=AUTH_HEADER,
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

    keycloak_mock.group_get_name.return_value = 'foobar-group'

    rv = client.post(
        f'{API_BASE}/lab/region',
        headers=AUTH_HEADER,
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


def test_create_region_unauthorized(client, db_session_mock):
    group_id = '10000000-2000-3000-4000-000000000000'
    region_data = {
        'name': 'test',
        'location_id': 1,
        'tower_id': 1,
        'openstack_id': 1,
        'owner_group_id': group_id,
    }

    rv = client.post(
        f'{API_BASE}/lab/region',
        json=region_data,
    )

    db_session_mock.add.assert_not_called()

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


@pytest.mark.parametrize(
    'region_data, missing_property',
    [
        pytest.param(
            {
                'owner_group_id': '10000000-2000-3000-4000-000000000000',
                'openstack_id': 1,
                'tower_id': 1,
            },
            'name',
            id='missing_name',
        ),
        pytest.param(
            {
                'name': 'test',
                'openstack_id': 1,
                'tower_id': 1,
            },
            'owner_group_id',
            id='missing_owner_group_id',
        ),
        pytest.param(
            {
                'name': 'test',
                'owner_group_id': '10000000-2000-3000-4000-000000000000',
                'tower_id': 1,
            },
            'openstack_id',
            id='missing_openstack_id',
        ),
        pytest.param(
            {
                'name': 'test',
                'owner_group_id': '10000000-2000-3000-4000-000000000000',
                'openstack_id': 1,
            },
            'tower_id',
            id='missing_tower_id',
        ),
    ],
)
def test_create_missing_properties(
    client, 
    db_session_mock, 
    region_data, 
    missing_property,
):
    rv = client.post(
        f'{API_BASE}/lab/region',
        headers=AUTH_HEADER,
        json=region_data,
    )

    db_session_mock.add.assert_not_called()

    assert rv.status_code == 400, rv.data
    assert rv.json['title'] == 'Bad Request'
    assert rv.json['detail'] == f'\'{missing_property}\' is a required property'


@pytest.mark.parametrize(
    'invalid_property',
    [
        pytest.param(
            'owner_group_id',
            id='invalid_owner_group_id',
        ),
        pytest.param(
            'tower_id',
            id='invalid_tower_id',
        ),
        pytest.param(
            'name',
            id='invalid_name',
        ),
    ],
)
def test_create_invalid_values(
    client,
    db_session_mock,
    keycloak_mock,
    invalid_property
):
    group_id = '10000000-2000-3000-4000-000000000000'
    region_data = {
        'name': 'test',
        'location_id': 1,
        'tower_id': 1,
        'openstack_id': 1,
        'owner_group_id': group_id,
    }

    if invalid_property == 'owner_group_id':
        keycloak_mock.group_get.side_effect = KeycloakGetError

        error_title = 'Group does not exist'
        error_detail = (
            f'Group {region_data["owner_group_id"]} does not exist in Keycloak,'
            ' you have to create group first or use existing group.'
        )
    else:
        keycloak_mock.group_get.side_effect = None
        keycloak_mock.group_get.return_value = 'foobar-group'

    if invalid_property == 'tower_id':
        model.tower_model.Server.query.get.return_value = None

        error_title = 'Not Found'
        error_detail = (
            f'Tower instance with ID {region_data["tower_id"]} does not exist'
        )
    else:
        model.tower_model.Server.query.get.return_value = model.tower_model.Server(
            id=region_data['tower_id'],
            name='tower',
            url='https://tower.example.com',
            credentials='kv/tower/prod/rhub'
        )

    if invalid_property == 'name':
        model.Region.query.filter.return_value.count.return_value = 1

        error_title = 'Bad Request'
        error_detail = (
            f'Region with name {region_data["name"]!r} already exists'
        )
    else:
        model.Region.query.filter.return_value.count.return_value = 1


    rv = client.post(
        f'{API_BASE}/lab/region',
        headers=AUTH_HEADER,
        json=region_data,
    )

    db_session_mock.add.assert_not_called()

    assert rv.status_code == 400, rv.data
    assert rv.json['title'] == error_title
    assert rv.json['detail'] == error_detail


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
        dns_id=None,
        dns=None,
    )
    model.Region.query.get.return_value = region

    rv = client.patch(
        f'{API_BASE}/lab/region/1',
        headers=AUTH_HEADER,
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
def test_update_region_quota(client, keycloak_mock, db_session_mock, quota_data):
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
        user_quota_id=1,
        user_quota=model.Quota(
            id=1,
            num_vcpus=40,
            ram_mb=200000,
            num_volumes=40,
            volumes_gb=540,
        ),
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
        dns_id=None,
        dns=None,
    )
    model.Region.query.get.return_value = region

    rv = client.patch(
        f'{API_BASE}/lab/region/1',
        headers=AUTH_HEADER,
        json={'user_quota': quota_data},
    )

    assert rv.status_code == 200, rv.data

    model.Region.query.get.assert_called_with(1)

    assert rv.json['user_quota'] == quota_data

    if quota_data is None:
        deleted_row = db_session_mock.delete.call_args.args[0]
        assert isinstance(deleted_row, model.Quota)


def test_update_region_unauthorized(client, db_session_mock):
    rv = client.patch(
        f'{API_BASE}/lab/region/1',
        json={
            'name': 'new',
            'description': 'new desc',
        },
    )

    db_session_mock.commit.assert_not_called()

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_update_region_non_existent(client, db_session_mock):
    region_id = 1

    model.Region.query.get.return_value = None

    rv = client.patch(
        f'{API_BASE}/lab/region/{region_id}',
        headers=AUTH_HEADER,
        json={
            'name': 'new',
            'description': 'new desc',
        },
    )

    model.Region.query.get.assert_called_with(region_id)
    db_session_mock.commit.assert_not_called()

    assert rv.status_code == 404, rv.data
    assert rv.json['title'] == 'Not Found'
    assert rv.json['detail'] == f'Region {region_id} does not exist'


@pytest.mark.parametrize(
    'new_data, invalid_property, table',
    [
        pytest.param(
            {'name': 'new'},
            'name',
            '',
            id='invalid_name',
        ),
        pytest.param(
            {'tower_id': 42},
            'tower_id',
            'tower_server',
            id='invalid_tower_id',
        ),
        pytest.param(
            {'openstack_id': 42},
            'openstack_id',
            'openstack_cloud',
            id='invalid_openstack_id',
        ),
        pytest.param(
            {'owner_group_id': '10000000-2000-3000-4000-000000000000'},
            'owner_group_id',
            '',
            id='invalid_owner_group_id',
        ),
    ],
)
def test_update_region_invalid_values(
    client,
    keycloak_mock,
    db_unique_violation,
    db_foreign_key_violation, 
    new_data, 
    invalid_property,
    table,
):
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
        dns_id=None,
        dns=None,
    )
    model.Region.query.get.return_value = region

    error_title = 'Bad Request'
    if invalid_property == 'name':
        db_unique_violation('name', new_data['name'])

        error_detail = f'Key (name)=({new_data["name"]}) already exists.'
    
    if invalid_property in ['tower_id', 'openstack_id']:
        db_foreign_key_violation(
            invalid_property,
            new_data[invalid_property],
            table
        )

        error_detail = (
            f'Key ({invalid_property})=({new_data[invalid_property]}) is not '
            f'present in table "{table}".'
        )

    if invalid_property == 'owner_group_id':
        keycloak_mock.group_get.side_effect = KeycloakGetError

        error_title = 'Group does not exist'
        error_detail = (
            f'Group {new_data["owner_group_id"]} does not exist in Keycloak, '
            f'you have to create group first or use existing group.'
        )

    rv = client.patch(
        f'{API_BASE}/lab/region/{region.id}',
        headers=AUTH_HEADER,
        json=new_data,
    )

    model.Region.query.get.assert_called_with(region.id)

    assert rv.status_code == 400, rv.data
    assert rv.json['title'] == error_title
    assert rv.json['detail'] == error_detail
    

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
        dns_id=None,
        dns=None,
    )
    model.Region.query.get.return_value = region
    model.RegionProduct.query.filter.return_value.count.return_value = 0

    rv = client.delete(
        f'{API_BASE}/lab/region/1',
        headers=AUTH_HEADER,
    )

    assert rv.status_code == 204, rv.data

    model.Region.query.get.assert_called_with(1)
    db_session_mock.delete.assert_called_with(region)


def test_delete_region_unauthorized(client, db_session_mock):
    rv = client.delete(
        f'{API_BASE}/lab/region/1',
    )

    db_session_mock.delete.assert_not_called()

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_delete_region_non_existent(client, db_session_mock):
    region_id = 1

    model.Region.query.get.return_value = None

    rv = client.delete(
        f'{API_BASE}/lab/region/{region_id}',
        headers=AUTH_HEADER,
    )

    model.Region.query.get.assert_called_with(region_id)

    db_session_mock.delete.assert_not_called()

    assert rv.status_code == 404, rv.data
    assert rv.json['title'] == 'Not Found'
    assert rv.json['detail'] == f'Region {region_id} does not exist'


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
        dns_id=None,
        dns=None,
        products_relation=products_relation
    )

    rv = client.get(
        f'{API_BASE}/lab/region/1/products',
        headers=AUTH_HEADER,
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


def test_region_list_products_unauthorized(client):
    rv = client.get(
        f'{API_BASE}/lab/region/1/products',
    )

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


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
        dns_id=None,
        dns=None,
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
        headers=AUTH_HEADER,
        json={'id': 10},
    )

    assert rv.status_code == 204, rv.data

    db_session_mock.add.assert_called()
    db_session_mock.commit.assert_called()

    region_product = db_session_mock.add.call_args.args[0]
    assert region_product.region_id == 1
    assert region_product.product_id == 10
    assert region_product.enabled is True


def test_region_add_product_unauthorized(client, db_session_mock):
    rv = client.post(
        f'{API_BASE}/lab/region/1/products',
        json={'id': 10},
    )

    db_session_mock.add.assert_not_called()

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_region_add_product_non_existent(client, db_session_mock):
    product_id = 10

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
        dns_id=None,
        dns=None,
        products_relation=[],
    )
    model.Region.query.get.return_value = region

    model.Product.query.get.return_value = None
    model.RegionProduct.query.filter.return_value.count.return_value = 0

    rv = client.post(
        f'{API_BASE}/lab/region/{region.id}/products',
        headers=AUTH_HEADER,
        json={'id': product_id},
    )

    model.Region.query.get.assert_called_with(region.id)
    model.Product.query.get.assert_called_with(product_id)
    
    db_session_mock.add.assert_not_called

    assert rv.status_code == 404, rv.data
    assert rv.json['title'] == 'Not Found'
    assert rv.json['detail'] == f'Product {product_id} does not exist'


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
        dns_id=None,
        dns=None,
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
        headers=AUTH_HEADER,
        json={'id': 10, 'enabled': False},
    )

    assert rv.status_code == 204, rv.data

    db_session_mock.commit.assert_called()

    assert region_product.enabled is False


def test_region_disable_product_unauthorized(client, db_session_mock):
    rv = client.post(
        f'{API_BASE}/lab/region/1/products',
        json={'id': 10, 'enabled': False},
    )

    db_session_mock.commit.assert_not_called()

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


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
        dns_id=None,
        dns=None,
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
        headers=AUTH_HEADER,
        json={'id': 10},
    )

    assert rv.status_code == 204, rv.data

    db_session_mock.delete.assert_called_with(region_product)
    db_session_mock.commit.assert_called()


def test_region_delete_product_unauthorized(client, db_session_mock):
    rv = client.delete(
        f'{API_BASE}/lab/region/1/products',
        json={'id': 10},
    )

    db_session_mock.delete.assert_not_called()

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'
