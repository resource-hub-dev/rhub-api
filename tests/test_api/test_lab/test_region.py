import base64
from unittest.mock import ANY

import pytest
import sqlalchemy.exc

from rhub.lab import model
from rhub.auth.keycloak import KeycloakClient
from rhub.api.vault import Vault
from rhub.api.lab.region import VAULT_PATH_PREFIX


API_BASE = '/v0'


def _db_add_row_side_effect(data_added):
    def side_effect(row):
        for k, v in data_added.items():
            setattr(row, k, v)
    return side_effect


def test_to_dict(keycloak_mock):
    region = model.Region(
        id=1,
        name='test',
        location='RDU',
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
        owner_group='00000000-0000-0000-0000-000000000000',
        users_group=None,
        tower_id=1,
        openstack_url='https://openstack.example.com:13000',
        openstack_credentials='kv/example/openstack',
        openstack_project='rhub',
        openstack_domain_name='Default',
        openstack_domain_id='default',
        openstack_networks=['provider_net_rhub'],
        openstack_keyname='rhub_key',
        satellite_hostname='satellite.example.com',
        satellite_insecure=False,
        satellite_credentials='kv/example/satellite',
        dns_server_hostname='ns.example.com',
        dns_server_zone='example.com.',
        dns_server_key='kv/example/key',
        vault_server='https://vault.example.com/',
        download_server='https://download.example.com',
    )

    keycloak_mock.group_get.return_value = {'name': 'foobar-group'}

    assert region.to_dict() == {
        'id': 1,
        'name': 'test',
        'location': 'RDU',
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
        'owner_group': '00000000-0000-0000-0000-000000000000',
        'owner_group_name': 'foobar-group',
        'users_group': None,
        'users_group_name': None,
        'tower_id': 1,
        'openstack': {
            'url': 'https://openstack.example.com:13000',
            'credentials': 'kv/example/openstack',
            'project': 'rhub',
            'domain_name': 'Default',
            'domain_id': 'default',
            'networks': ['provider_net_rhub'],
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
            'key': 'kv/example/key',
        },
        'vault_server': 'https://vault.example.com/',
        'download_server': 'https://download.example.com',
    }


def test_list_regions(client, keycloak_mock):
    model.Region.query.limit.return_value.offset.return_value = [
        model.Region(
            id=1,
            name='test',
            location='RDU',
            description='',
            banner='',
            enabled=True,
            user_quota_id=None,
            total_quota_id=None,
            lifespan_length=None,
            reservations_enabled=True,
            reservation_expiration_max=7,
            owner_group='00000000-0000-0000-0000-000000000000',
            users_group=None,
            tower_id=1,
            openstack_url='https://openstack.example.com:13000',
            openstack_credentials='kv/example/openstack',
            openstack_project='rhub',
            openstack_domain_name='Default',
            openstack_domain_id='default',
            openstack_networks=['provider_net_rhub'],
            openstack_keyname='rhub_key',
            satellite_hostname='satellite.example.com',
            satellite_insecure=False,
            satellite_credentials='kv/example/satellite',
            dns_server_hostname='ns.example.com',
            dns_server_zone='example.com.',
            dns_server_key='kv/example/key',
            vault_server='https://vault.example.com/',
            download_server='https://download.example.com',
        ),
    ]
    model.Region.query.count.return_value = 1

    keycloak_mock.group_get.return_value = {'name': 'foobar-group'}

    rv = client.get(
        f'{API_BASE}/lab/region',
        headers={'Authorization': 'Bearer foobar'},
    )

    assert rv.status_code == 200
    assert rv.json == {
        'data': [
            {
                'id': 1,
                'name': 'test',
                'location': 'RDU',
                'description': '',
                'banner': '',
                'enabled': True,
                'user_quota': None,
                'total_quota': None,
                'lifespan_length': None,
                'reservations_enabled': True,
                'reservation_expiration_max': 7,
                'owner_group': '00000000-0000-0000-0000-000000000000',
                'owner_group_name': 'foobar-group',
                'users_group': None,
                'users_group_name': None,
                'tower_id': 1,
                'openstack': {
                    'url': 'https://openstack.example.com:13000',
                    'credentials': 'kv/example/openstack',
                    'project': 'rhub',
                    'domain_name': 'Default',
                    'domain_id': 'default',
                    'networks': ['provider_net_rhub'],
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
                    'key': 'kv/example/key',
                },
                'vault_server': 'https://vault.example.com/',
                'download_server': 'https://download.example.com',
                '_href': ANY,
            }
        ],
        'total': 1,
    }


def test_get_region(client, keycloak_mock):
    model.Region.query.get.return_value = model.Region(
        id=1,
        name='test',
        location='RDU',
        description='',
        banner='',
        enabled=True,
        user_quota_id=None,
        total_quota_id=None,
        lifespan_length=None,
        reservations_enabled=True,
        reservation_expiration_max=7,
        owner_group='00000000-0000-0000-0000-000000000000',
        users_group=None,
        tower_id=1,
        openstack_url='https://openstack.example.com:13000',
        openstack_credentials='kv/example/openstack',
        openstack_project='rhub',
        openstack_domain_name='Default',
        openstack_domain_id='default',
        openstack_networks=['provider_net_rhub'],
        openstack_keyname='rhub_key',
        satellite_hostname='satellite.example.com',
        satellite_insecure=False,
        satellite_credentials='kv/example/satellite',
        dns_server_hostname='ns.example.com',
        dns_server_zone='example.com.',
        dns_server_key='kv/example/key',
        vault_server='https://vault.example.com/',
        download_server='https://download.example.com',
    )

    keycloak_mock.group_get.return_value = {'name': 'foobar-group'}

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
        'user_quota': None,
        'total_quota': None,
        'lifespan_length': None,
        'reservations_enabled': True,
        'reservation_expiration_max': 7,
        'owner_group': '00000000-0000-0000-0000-000000000000',
        'owner_group_name': 'foobar-group',
        'users_group': None,
        'users_group_name': None,
        'tower_id': 1,
        'openstack': {
            'url': 'https://openstack.example.com:13000',
            'credentials': 'kv/example/openstack',
            'project': 'rhub',
            'domain_name': 'Default',
            'domain_id': 'default',
            'networks': ['provider_net_rhub'],
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
            'key': 'kv/example/key',
        },
        'vault_server': 'https://vault.example.com/',
        'download_server': 'https://download.example.com',
        '_href': ANY,
    }


def test_create_region(client, db_session_mock, keycloak_mock, mocker):
    region_data = {
        'name': 'test',
        'location': 'RDU',
        'tower_id': 1,
        'openstack': {
            'url': 'https://openstack.example.com:13000',
            'credentials': 'kv/example/openstack',
            'project': 'rhub',
            'domain_name': 'Default',
            'domain_id': 'default',
            'networks': ['provider_net_rhub'],
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
            'key': 'kv/example/key',
        },
        'vault_server': 'https://vault.example.com/',
        'download_server': 'https://download.example.com',
    }
    group_id = '10000000-2000-3000-4000-000000000000'

    model.Region.query.filter.return_value.count.return_value = 0
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
        if isinstance(v, dict):
            for k2, v2 in v.items():
                assert getattr(region, f'{k}_{k2}') == v2
        else:
            assert getattr(region, k) == v

    assert rv.status_code == 200
    assert rv.json['user_quota'] is None
    assert rv.json['owner_group'] == group_id
    assert rv.json['users_group'] is None


def test_create_region_credentials(client, db_session_mock, keycloak_mock, vault_mock):
    region_data = {
        'name': 'test',
        'location': 'RDU',
        'tower_id': 1,
        'openstack': {
            'url': 'https://openstack.example.com:13000',
            'credentials': {
                'username': 'osp-user',
                'password': 'osp-pass',
            },
            'project': 'rhub',
            'domain_name': 'Default',
            'domain_id': 'default',
            'networks': ['provider_net_rhub'],
            'keyname': 'rhub_key',
        },
        'satellite': {
            'hostname': 'satellite.example.com',
            'insecure': False,
            'credentials': {
                'username': 'sat-user',
                'password': 'sat-pass',
            },
        },
        'dns_server': {
            'hostname': 'ns.example.com',
            'zone': 'example.com.',
            'key': {
                'name': 'rndc-key',
                'secret': 'abcdef==',
            },
        },
        'vault_server': 'https://vault.example.com/',
        'download_server': 'https://download.example.com',
    }
    group_id = '10000000-2000-3000-4000-000000000000'

    model.Region.query.filter.return_value.count.return_value = 0
    db_session_mock.add.side_effect = _db_add_row_side_effect({'id': 1})

    keycloak_mock.group_create.return_value = group_id

    rv = client.post(
        f'{API_BASE}/lab/region',
        headers={'Authorization': 'Bearer foobar'},
        json=region_data,
    )

    assert rv.status_code == 200

    assert type(rv.json['openstack']['credentials']) is str
    assert rv.json['openstack']['credentials'].startswith(f'{VAULT_PATH_PREFIX}/')
    vault_mock.write.assert_any_call(
        rv.json['openstack']['credentials'],
        {'username': 'osp-user', 'password': 'osp-pass'},
    )

    assert type(rv.json['satellite']['credentials']) is str
    assert rv.json['satellite']['credentials'].startswith(f'{VAULT_PATH_PREFIX}/')
    vault_mock.write.assert_any_call(
        rv.json['satellite']['credentials'],
        {'username': 'sat-user', 'password': 'sat-pass'},
    )

    assert type(rv.json['dns_server']['key']) is str
    assert rv.json['dns_server']['key'].startswith(f'{VAULT_PATH_PREFIX}/')
    vault_mock.write.assert_any_call(
        rv.json['dns_server']['key'],
        {'name': 'rndc-key', 'secret': 'abcdef=='},
    )


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
        'user_quota': quota_data,
        'total_quota': None,
        'openstack': {
            'url': 'https://openstack.example.com:13000',
            'credentials': 'kv/example/openstack',
            'project': 'rhub',
            'domain_name': 'Default',
            'domain_id': 'default',
            'networks': ['provider_net_rhub'],
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
            'key': 'kv/example/key',
        },
        'vault_server': 'https://vault.example.com/',
        'download_server': 'https://download.example.com',
    }
    group_id = '10000000-2000-3000-4000-000000000000'

    model.Region.query.filter.return_value.count.return_value = 0
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

    assert rv.status_code == 200
    assert rv.json['user_quota'] == quota_data
    assert rv.json['owner_group'] == group_id
    assert rv.json['users_group'] is None


def test_create_region_fail_keycloak_cleanup(client, db_session_mock, keycloak_mock):
    region_data = {
        'name': 'test',
        'location': 'RDU',
        'tower_id': 1,
        'openstack': {
            'url': 'https://openstack.example.com:13000',
            'credentials': 'kv/example/openstack',
            'project': 'rhub',
            'domain_name': 'Default',
            'domain_id': 'default',
            'networks': ['provider_net_rhub'],
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
            'key': 'kv/example/key',
        },
        'vault_server': 'https://vault.example.com/',
        'download_server': 'https://download.example.com',
    }
    group_id = '10000000-2000-3000-4000-000000000000'

    model.Region.query.filter.return_value.count.return_value = 0
    db_session_mock.add.side_effect = _db_add_row_side_effect({'id': 1})
    db_session_mock.commit.side_effect = sqlalchemy.exc.SQLAlchemyError

    keycloak_mock.group_create.return_value = group_id

    rv = client.post(
        f'{API_BASE}/lab/region',
        headers={'Authorization': 'Bearer foobar'},
        json=region_data,
    )

    keycloak_mock.group_create.assert_called_with({'name': 'test-owners'})

    db_session_mock.add.assert_called()

    keycloak_mock.group_delete.called_with(group_id)

    assert rv.status_code == 500


def test_update_region(client):
    region = model.Region(
        id=1,
        name='test',
        location='RDU',
        description='',
        banner='',
        enabled=True,
        user_quota_id=None,
        total_quota_id=None,
        lifespan_length=None,
        reservations_enabled=True,
        reservation_expiration_max=7,
        owner_group='00000000-0000-0000-0000-000000000000',
        users_group=None,
        tower_id=1,
        openstack_url='https://openstack.example.com:13000',
        openstack_credentials='kv/example/openstack',
        openstack_project='rhub',
        openstack_domain_name='Default',
        openstack_domain_id='default',
        openstack_networks=['provider_net_rhub'],
        openstack_keyname='rhub_key',
        satellite_hostname='satellite.example.com',
        satellite_insecure=False,
        satellite_credentials='kv/example/satellite',
        dns_server_hostname='ns.example.com',
        dns_server_zone='example.com.',
        dns_server_key='kv/example/key',
        vault_server='https://vault.example.com/',
        download_server='https://download.example.com',
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


def test_update_region_credentials(client, vault_mock):
    region = model.Region(
        id=1,
        name='test',
        location='RDU',
        description='',
        banner='',
        enabled=True,
        user_quota_id=None,
        total_quota_id=None,
        lifespan_length=None,
        reservations_enabled=True,
        reservation_expiration_max=7,
        owner_group='00000000-0000-0000-0000-000000000000',
        users_group=None,
        tower_id=1,
        openstack_url='https://openstack.example.com:13000',
        openstack_credentials='kv/example/openstack',
        openstack_project='rhub',
        openstack_domain_name='Default',
        openstack_domain_id='default',
        openstack_networks=['provider_net_rhub'],
        openstack_keyname='rhub_key',
        satellite_hostname='satellite.example.com',
        satellite_insecure=False,
        satellite_credentials='kv/example/satellite',
        dns_server_hostname='ns.example.com',
        dns_server_zone='example.com.',
        dns_server_key='kv/example/key',
        vault_server='https://vault.example.com/',
        download_server='https://download.example.com',
    )
    model.Region.query.get.return_value = region

    rv = client.patch(
        f'{API_BASE}/lab/region/1',
        headers={'Authorization': 'Bearer foobar'},
        json={
            'openstack': {
                'credentials': {
                    'username': 'new-osp-user',
                    'password': 'new-osp-pass',
                },
            },
            'satellite': {
                'credentials': {
                    'username': 'new-sat-user',
                    'password': 'new-sat-pass',
                },
            },
            'dns_server': {
                'key': {
                    'name': 'new-rndc-key',
                    'secret': 'abc=',
                },
            },
        },
    )

    model.Region.query.get.assert_called_with(1)

    assert rv.status_code == 200

    # Check that path didn't change
    assert region.openstack_credentials == 'kv/example/openstack'
    assert region.satellite_credentials == 'kv/example/satellite'
    assert region.dns_server_key == 'kv/example/key'

    vault_mock.write.assert_any_call(
        'kv/example/openstack',
        {'username': 'new-osp-user', 'password': 'new-osp-pass'},
    )

    vault_mock.write.assert_any_call(
        'kv/example/satellite',
        {'username': 'new-sat-user', 'password': 'new-sat-pass'},
    )

    vault_mock.write.assert_any_call(
        'kv/example/key',
        {'name': 'new-rndc-key', 'secret': 'abc='},
    )



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
        user_quota_id=None,
        total_quota_id=None,
        lifespan_length=None,
        reservations_enabled=True,
        reservation_expiration_max=7,
        owner_group='00000000-0000-0000-0000-000000000000',
        users_group=None,
        tower_id=1,
        openstack_url='https://openstack.example.com:13000',
        openstack_credentials='kv/example/openstack',
        openstack_project='rhub',
        openstack_domain_name='Default',
        openstack_domain_id='default',
        openstack_networks=['provider_net_rhub'],
        openstack_keyname='rhub_key',
        satellite_hostname='satellite.example.com',
        satellite_insecure=False,
        satellite_credentials='kv/example/satellite',
        dns_server_hostname='ns.example.com',
        dns_server_zone='example.com.',
        dns_server_key='kv/example/key',
        vault_server='https://vault.example.com/',
        download_server='https://download.example.com',
    )
    model.Region.query.get.return_value = region

    rv = client.patch(
        f'{API_BASE}/lab/region/1',
        headers={'Authorization': 'Bearer foobar'},
        json={'user_quota': quota_data},
    )

    model.Region.query.get.assert_called_with(1)

    assert rv.status_code == 200
    assert rv.json['user_quota'] == quota_data



@pytest.mark.parametrize(
    'update_data',
    [
        pytest.param(
            {
                'openstack': {'credentials': 'kv/example/new-path/ocp'},
            },
            id='openstack',
        ),
        pytest.param(
            {
                'satellite': {'hostname': 'new-satellite.example.com'},
            },
            id='satellite',
        ),
        pytest.param(
            {
                'dns_server': {'hostname': 'new-ns.example.com'},
            },
            id='dns_server'
        ),
        pytest.param(
            {
                'openstack': {'credentials': 'kv/example/new-path/ocp'},
                'satellite': {'hostname': 'new-satellite.example.com'},
                'dns_server': {'hostname': 'new-ns.example.com'},
            },
            id='ALL',
        ),
    ]
)
def test_update_region_nested_data(client, update_data):
    region = model.Region(
        id=1,
        name='test',
        location='RDU',
        description='',
        banner='',
        enabled=True,
        user_quota_id=None,
        total_quota_id=None,
        lifespan_length=None,
        reservations_enabled=True,
        reservation_expiration_max=7,
        owner_group='00000000-0000-0000-0000-000000000000',
        users_group=None,
        tower_id=1,
        openstack_url='https://openstack.example.com:13000',
        openstack_credentials='kv/example/openstack',
        openstack_project='rhub',
        openstack_domain_name='Default',
        openstack_domain_id='default',
        openstack_networks=['provider_net_rhub'],
        openstack_keyname='rhub_key',
        satellite_hostname='satellite.example.com',
        satellite_insecure=False,
        satellite_credentials='kv/example/satellite',
        dns_server_hostname='ns.example.com',
        dns_server_zone='example.com.',
        dns_server_key='kv/example/key',
        vault_server='https://vault.example.com/',
        download_server='https://download.example.com',
    )
    model.Region.query.get.return_value = region

    rv = client.patch(
        f'{API_BASE}/lab/region/1',
        headers={'Authorization': 'Bearer foobar'},
        json=update_data,
    )

    model.Region.query.get.assert_called_with(1)

    assert rv.status_code == 200

    for k1 in update_data.keys():
        for k2, v in update_data[k1].items():
            assert getattr(region, f'{k1}_{k2}') == v
            assert rv.json[k1][k2] == v


def test_delete_region(client, keycloak_mock, db_session_mock):
    group_id = '00000000-0000-0000-0000-000000000000'
    region = model.Region(
        id=1,
        name='test',
        location='RDU',
        description='',
        banner='',
        enabled=True,
        user_quota_id=None,
        total_quota_id=None,
        lifespan_length=None,
        reservations_enabled=True,
        reservation_expiration_max=7,
        owner_group=group_id,
        users_group=None,
        tower_id=1,
    )
    model.Region.query.get.return_value = region
    model.RegionProduct.query.filter.return_value.count.return_value = 0

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
        location='RDU',
        description='',
        banner='',
        enabled=True,
        user_quota_id=None,
        total_quota_id=None,
        lifespan_length=None,
        reservations_enabled=True,
        reservation_expiration_max=7,
        owner_group='00000000-0000-0000-0000-000000000000',
        users_group=None,
        tower_id=1,
        openstack_url='https://openstack.example.com:13000',
        openstack_credentials='kv/example/openstack',
        openstack_project='rhub',
        openstack_domain_name='Default',
        openstack_domain_id='default',
        openstack_networks=['provider_net_rhub'],
        openstack_keyname='rhub_key',
        satellite_hostname='satellite.example.com',
        satellite_insecure=False,
        satellite_credentials='kv/example/satellite',
        dns_server_hostname='ns.example.com',
        dns_server_zone='example.com.',
        dns_server_key='kv/example/key',
        vault_server='https://vault.example.com/',
        download_server='https://download.example.com',
        products_relation=products_relation
    )

    rv = client.get(
        f'{API_BASE}/lab/region/1/products',
        headers={'Authorization': 'Bearer foobar'},
    )

    assert rv.status_code == 200
    assert rv.json == [
        {
            'id': 1,
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
        location='RDU',
        description='',
        banner='',
        enabled=True,
        user_quota_id=None,
        total_quota_id=None,
        lifespan_length=None,
        reservations_enabled=True,
        reservation_expiration_max=7,
        owner_group='00000000-0000-0000-0000-000000000000',
        users_group=None,
        tower_id=1,
        openstack_url='https://openstack.example.com:13000',
        openstack_credentials='kv/example/openstack',
        openstack_project='rhub',
        openstack_domain_name='Default',
        openstack_domain_id='default',
        openstack_networks=['provider_net_rhub'],
        openstack_keyname='rhub_key',
        satellite_hostname='satellite.example.com',
        satellite_insecure=False,
        satellite_credentials='kv/example/satellite',
        dns_server_hostname='ns.example.com',
        dns_server_zone='example.com.',
        dns_server_key='kv/example/key',
        vault_server='https://vault.example.com/',
        download_server='https://download.example.com',
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

    assert rv.status_code == 204

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
        location='RDU',
        description='',
        banner='',
        enabled=True,
        user_quota_id=None,
        total_quota_id=None,
        lifespan_length=None,
        reservations_enabled=True,
        reservation_expiration_max=7,
        owner_group='00000000-0000-0000-0000-000000000000',
        users_group=None,
        tower_id=1,
        openstack_url='https://openstack.example.com:13000',
        openstack_credentials='kv/example/openstack',
        openstack_project='rhub',
        openstack_domain_name='Default',
        openstack_domain_id='default',
        openstack_networks=['provider_net_rhub'],
        openstack_keyname='rhub_key',
        satellite_hostname='satellite.example.com',
        satellite_insecure=False,
        satellite_credentials='kv/example/satellite',
        dns_server_hostname='ns.example.com',
        dns_server_zone='example.com.',
        dns_server_key='kv/example/key',
        vault_server='https://vault.example.com/',
        download_server='https://download.example.com',
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

    assert rv.status_code == 204

    db_session_mock.commit.assert_called()

    assert region_product.enabled is False


def test_region_delete_product(client, db_session_mock):
    model.Region.query.get.return_value = model.Region(
        id=1,
        name='test',
        location='RDU',
        description='',
        banner='',
        enabled=True,
        user_quota_id=None,
        total_quota_id=None,
        lifespan_length=None,
        reservations_enabled=True,
        reservation_expiration_max=7,
        owner_group='00000000-0000-0000-0000-000000000000',
        users_group=None,
        tower_id=1,
        openstack_url='https://openstack.example.com:13000',
        openstack_credentials='kv/example/openstack',
        openstack_project='rhub',
        openstack_domain_name='Default',
        openstack_domain_id='default',
        openstack_networks=['provider_net_rhub'],
        openstack_keyname='rhub_key',
        satellite_hostname='satellite.example.com',
        satellite_insecure=False,
        satellite_credentials='kv/example/satellite',
        dns_server_hostname='ns.example.com',
        dns_server_zone='example.com.',
        dns_server_key='kv/example/key',
        vault_server='https://vault.example.com/',
        download_server='https://download.example.com',
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

    assert rv.status_code == 204

    db_session_mock.delete.assert_called_with(region_product)
    db_session_mock.commit.assert_called()
