import base64

import pytest
import sqlalchemy.exc

from rhub.lab import model
from rhub.auth.keycloak import KeycloakClient
from rhub.api.vault import Vault
from rhub.api.lab.region import VAULT_PATH_PREFIX


API_BASE = '/v0'


@pytest.fixture(autouse=True)
def keycloak_mock(mocker):
    keycloak_mock = mocker.Mock(spec=KeycloakClient)

    get_keycloak_mock = mocker.patch(f'rhub.api.lab.region.get_keycloak')
    get_keycloak_mock.return_value = keycloak_mock

    yield keycloak_mock


@pytest.fixture(autouse=True)
def vault_mock(mocker):
    vault_mock = mocker.Mock()
    mocker.patch('rhub.api.lab.region.get_vault').return_value = vault_mock
    yield vault_mock


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
        'reservation_expiration_max': 7,
        'owner_group': '00000000-0000-0000-0000-000000000000',
        'users_group': None,
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
            'reservation_expiration_max': 7,
            'owner_group': '00000000-0000-0000-0000-000000000000',
            'users_group': None,
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
        'reservation_expiration_max': 7,
        'owner_group': '00000000-0000-0000-0000-000000000000',
        'users_group': None,
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
    assert rv.json['quota'] is None
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
        'quota': quota_data,
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
        if isinstance(v, dict):
            for k2, v2 in v.items():
                assert getattr(region, f'{k}_{k2}') == v2
        else:
            assert getattr(region, k) == v

    assert region.quota is not None
    for k, v in quota_data.items():
        assert getattr(region.quota, k) == v

    assert rv.status_code == 200
    assert rv.json['quota'] == quota_data
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
        quota_id=None,
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
        quota_id=None,
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
        quota_id=None,
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
        json={'quota': quota_data},
    )

    model.Region.query.get.assert_called_with(1)

    assert rv.status_code == 200
    assert rv.json['quota'] == quota_data



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
        quota_id=None,
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
        quota_id=None,
        lifespan_length=None,
        reservations_enabled=True,
        reservation_expiration_max=7,
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
