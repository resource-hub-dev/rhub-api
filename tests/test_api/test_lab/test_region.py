import base64

import pytest

from rhub.lab import model
from rhub.auth.keycloak import KeycloakClient


API_BASE = '/v0'


@pytest.fixture(autouse=True)
def keycloak_mock(mocker):
    keycloak_mock = mocker.Mock(spec=KeycloakClient)

    get_keycloak_mock = mocker.patch(f'rhub.api.lab.region.get_keycloak')
    get_keycloak_mock.return_value = keycloak_mock

    yield keycloak_mock


def _db_add_row_side_effect(data_added):
    def side_effect(row):
        for k, v in data_added.items():
            setattr(row, k, v)
    return side_effect


def test_to_dict():
    region = model.Region(
        id=1,
        name='test',
        location='RDU',
        description='desc',
        banner='ban',
        enabled=True,
        quota_id=1,
        quota=model.Quota(
            num_vcpus=40,
            ram_mb=200000,
            num_volumes=40,
            volumes_gb=540,
        ),
        lifespan_length=None,
        reservations_enabled=True,
        owner_group='00000000-0000-0000-0000-000000000000',
        users_group=None,
        tower_id=1,
        openstack_url='https://openstack.example.com:13000',
        openstack_credentials='kv/example/openstack',
        openstack_project='rhub',
        openstack_domain_name='Default',
        openstack_domain_id='default',
        openstack_default_project='rhub',
        openstack_default_network='provider_net_rhub',
        openstack_keyname='rhub_key',
        satellite_hostname='satellite.example.com',
        satellite_insecure=False,
        satellite_credentials='kv/example/satellite',
        dns_server_hostname='ns.example.com',
        dns_server_zone='example.com.',
        dns_server_key='example_key',
        vault_server='https://vault.example.com/',
        download_server='https://download.example.com',
    )

    assert region.to_dict() == {
        'id': 1,
        'name': 'test',
        'location': 'RDU',
        'description': 'desc',
        'banner':'ban',
        'enabled': True,
        'quota': {
            'num_vcpus': 40,
            'ram_mb': 200000,
            'num_volumes': 40,
            'volumes_gb': 540,
        },
        'lifespan_length': None,
        'reservations_enabled': True,
        'owner_group': '00000000-0000-0000-0000-000000000000',
        'users_group': None,
        'tower_id': 1,
        'openstack': {
            'url': 'https://openstack.example.com:13000',
            'credentials': 'kv/example/openstack',
            'project': 'rhub',
            'domain_name': 'Default',
            'domain_id': 'default',
            'default_project': 'rhub',
            'default_network': 'provider_net_rhub',
            'keyname': 'rhub_key',
        },
        'satellite': {
            'hostname': 'satellite.example.com',
            'insecure': False,
            'credentials': 'kv/example/satellite',
        },
        'dns_server': {
            'hostname': 'ns.example.com',
            'zone': 'example.com.',
            'key': 'example_key',
        },
        'vault_server': 'https://vault.example.com/',
        'download_server': 'https://download.example.com',
    }


def test_list_regions(client):
    model.Region.query.all.return_value = [
        model.Region(
            id=1,
            name='test',
            location='RDU',
            description='',
            banner='',
            enabled=True,
            quota_id=None,
            lifespan_length=None,
            reservations_enabled=True,
            owner_group='00000000-0000-0000-0000-000000000000',
            users_group=None,
            tower_id=1,
        ),
    ]

    rv = client.get(
        f'{API_BASE}/lab/region',
        headers={'Authorization': 'Bearer foobar'},
    )

    assert rv.status_code == 200
    assert rv.json == [
        {
            'id': 1,
            'name': 'test',
            'location': 'RDU',
            'description': '',
            'banner': '',
            'enabled': True,
            'quota': None,
            'lifespan_length': None,
            'reservations_enabled': True,
            'owner_group': '00000000-0000-0000-0000-000000000000',
            'users_group': None,
            'tower_id': 1,
        }
    ]


def test_get_region(client):
    model.Region.query.get.return_value = model.Region(
        id=1,
        name='test',
        location='RDU',
        description='',
        banner='',
        enabled=True,
        quota_id=None,
        lifespan_length=None,
        reservations_enabled=True,
        owner_group='00000000-0000-0000-0000-000000000000',
        users_group=None,
        tower_id=1,
    )

    rv = client.get(
        f'{API_BASE}/lab/region/1',
        headers={'Authorization': 'Bearer foobar'},
    )

    model.Region.query.get.assert_called_with(1)

    assert rv.status_code == 200
    assert rv.json == {
        'id': 1,
        'name': 'test',
        'location': 'RDU',
        'description': '',
        'banner': '',
        'enabled': True,
        'quota': None,
        'lifespan_length': None,
        'reservations_enabled': True,
        'owner_group': '00000000-0000-0000-0000-000000000000',
        'users_group': None,
        'tower_id': 1,
    }


def test_create_region(client, db_session_mock, keycloak_mock, mocker):
    region_data = {
        'name': 'test',
        'location': 'RDU',
        'tower_id': 1,
    }
    group_id = '10000000-2000-3000-4000-000000000000'

    db_session_mock.add.side_effect = _db_add_row_side_effect({'id': 1})

    keycloak_mock.group_create.return_value = group_id

    rv = client.post(
        f'{API_BASE}/lab/region',
        headers={'Authorization': 'Bearer foobar'},
        json=region_data,
    )

    db_session_mock.add.assert_called()

    keycloak_mock.group_create.assert_called_with({'name': 'test-owners'})

    region = db_session_mock.add.call_args.args[0]
    for k, v in region_data.items():
        assert getattr(region, k) == v

    assert rv.status_code == 200
    assert rv.json['quota'] is None
    assert rv.json['owner_group'] == group_id
    assert rv.json['users_group'] is None


def test_create_region_with_quota(client, db_session_mock, keycloak_mock, mocker):
    quota_data = {
        'num_vcpus': 40,
        'ram_mb': 200000,
        'num_volumes': 40,
        'volumes_gb': 540,
    }
    region_data = {
        'name': 'test',
        'location': 'RDU',
        'tower_id': 1,
        'quota': quota_data,
    }
    group_id = '10000000-2000-3000-4000-000000000000'

    db_session_mock.add.side_effect = _db_add_row_side_effect({'id': 1})

    keycloak_mock.group_create.return_value = group_id

    rv = client.post(
        f'{API_BASE}/lab/region',
        headers={'Authorization': 'Bearer foobar'},
        json=region_data,
    )

    db_session_mock.add.assert_called()

    keycloak_mock.group_create.assert_called_with({'name': 'test-owners'})

    region = db_session_mock.add.call_args.args[0]
    for k, v in region_data.items():
        if k == 'quota':
            continue
        assert getattr(region, k) == v

    assert region.quota is not None
    for k, v in quota_data.items():
        assert getattr(region.quota, k) == v

    assert rv.status_code == 200
    assert rv.json['quota'] == quota_data
    assert rv.json['owner_group'] == group_id
    assert rv.json['users_group'] is None


def test_update_region(client):
    region = model.Region(
        id=1,
        name='test',
        location='RDU',
        description='',
        banner='',
        enabled=True,
        quota_id=None,
        lifespan_length=None,
        reservations_enabled=True,
        owner_group='00000000-0000-0000-0000-000000000000',
        users_group=None,
        tower_id=1,
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

    model.Region.query.get.assert_called_with(1)

    assert region.name == 'new'
    assert region.description == 'new desc'

    assert rv.status_code == 200


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
        location='RDU',
        description='',
        banner='',
        enabled=True,
        quota_id=None,
        lifespan_length=None,
        reservations_enabled=True,
        owner_group='00000000-0000-0000-0000-000000000000',
        users_group=None,
        tower_id=1,
    )
    model.Region.query.get.return_value = region

    rv = client.patch(
        f'{API_BASE}/lab/region/1',
        headers={'Authorization': 'Bearer foobar'},
        json={'quota': quota_data},
    )

    model.Region.query.get.assert_called_with(1)

    assert rv.status_code == 200
    assert rv.json['quota'] == quota_data


def test_delete_region(client, keycloak_mock, db_session_mock):
    group_id = '00000000-0000-0000-0000-000000000000'
    region = model.Region(
        id=1,
        name='test',
        location='RDU',
        description='',
        banner='',
        enabled=True,
        quota_id=None,
        lifespan_length=None,
        reservations_enabled=True,
        owner_group=group_id,
        users_group=None,
        tower_id=1,
    )
    model.Region.query.get.return_value = region

    keycloak_mock.group_get.return_value = {
        'id': group_id,
        'name': 'test-owners',
    }
    keycloak_mock.group_delete.return_value = group_id

    rv = client.delete(
        f'{API_BASE}/lab/region/1',
        headers={'Authorization': 'Bearer foobar'},
    )

    model.Region.query.get.assert_called_with(1)
    db_session_mock.delete.assert_called_with(region)

    keycloak_mock.group_delete.assert_called_with(group_id)

    assert rv.status_code == 204
