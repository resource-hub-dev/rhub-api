import datetime

import pytest
from dateutil.tz import tzutc

from rhub.lab import model, SHAREDCLUSTER_USER, SHAREDCLUSTER_GROUP
from rhub.tower import model as tower_model
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


def _create_test_region():
    return model.Region(
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
        reservation_expiration_max=None,
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


def _create_test_product():
    return model.Product(
        id=1,
        name='dummy',
        description='dummy',
        enabled=True,
        tower_template_name_create='dummy-create',
        tower_template_name_delete='dummy-delete',
        parameters={},
    )


def test_list_clusters(client, keycloak_mock, mocker):
    user_id = '00000000-0000-0000-0000-000000000000'
    sample_region = _create_test_region()
    sample_product = _create_test_product()
    keycloak_mock.user_get.return_value = {'id': user_id, 'username': 'test-user'}
    model.Cluster.query.limit.return_value.offset.return_value = [
        model.Cluster(
            id=1,
            name='testcluster',
            description='test cluster',
            user_id='00000000-0000-0000-0000-000000000000',
            group_id=None,
            created=datetime.datetime(2021, 1, 1, 1, 0, 0, tzinfo=tzutc()),
            region_id=1,
            region=sample_region,
            reservation_expiration=None,
            lifespan_expiration=None,
            status=model.ClusterStatus.ACTIVE,
            product_id=1,
            product_params={},
            product=sample_product,
        ),
    ]
    mocker.patch.object(model.Cluster, 'hosts', [])
    mocker.patch.object(model.Cluster, 'quota', None)
    model.Cluster.query.count.return_value = 1

    rv = client.get(
        f'{API_BASE}/lab/cluster',
        headers={'Authorization': 'Bearer foobar'},
    )
    keycloak_mock.user_get.assert_called_with(user_id)

    assert rv.status_code == 200
    assert rv.json == {
        'data': [
            {
                'id': 1,
                'name': 'testcluster',
                'description': 'test cluster',
                'user_id': '00000000-0000-0000-0000-000000000000',
                'group_id': None,
                'created': '2021-01-01T01:00:00+00:00',
                'region_id': 1,
                'reservation_expiration': None,
                'lifespan_expiration': None,
                'status': model.ClusterStatus.ACTIVE.value,
                'region_name': 'test',
                'user_name': 'test-user',
                'group_name': None,
                'hosts': [],
                'quota': None,
                'quota_usage': None,
                'product_id': 1,
                'product_name': 'dummy',
                'product_params': {},
                'shared': False,
            },
        ],
        'total': 1,
    }


def test_get_cluster(client, keycloak_mock, mocker):
    user_id = '00000000-0000-0000-0000-000000000000'
    sample_region = _create_test_region()
    sample_product = _create_test_product()
    keycloak_mock.user_get.return_value = {'id': user_id, 'username': 'test-user'}

    model.Cluster.query.get.return_value = model.Cluster(
        id=1,
        name='testcluster',
        description='test cluster',
        user_id='00000000-0000-0000-0000-000000000000',
        group_id=None,
        created=datetime.datetime(2021, 1, 1, 1, 0, 0, tzinfo=tzutc()),
        region_id=1,
        region=sample_region,
        reservation_expiration=None,
        lifespan_expiration=None,
        status=model.ClusterStatus.ACTIVE,
        product_id=1,
        product_params={},
        product=sample_product,
    )
    mocker.patch.object(model.Cluster, 'hosts', [
        model.ClusterHost(
            id=1,
            cluster_id=1,
            fqdn='test0.localhost',
            ipaddr=['127.0.0.1', '::1'],
            num_vcpus=2,
            ram_mb=4096,
            num_volumes=1,
            volumes_gb=20,
        ),
        model.ClusterHost(
            id=2,
            cluster_id=1,
            fqdn='test1.localhost',
            ipaddr=['127.0.0.1', '::1'],
            num_vcpus=2,
            ram_mb=4096,
            num_volumes=1,
            volumes_gb=20,
        ),
    ])
    mocker.patch.object(model.Cluster, 'quota', model.Quota(
        id=1,
        num_vcpus=20,
        ram_mb=20000,
        num_volumes=2,
        volumes_gb=200,
    ))

    rv = client.get(
        f'{API_BASE}/lab/cluster/1',
        headers={'Authorization': 'Bearer foobar'},
    )

    assert rv.status_code == 200

    model.Cluster.query.get.assert_called_with(1)
    keycloak_mock.user_get.assert_called_with(user_id)

    assert rv.json == {
        'id': 1,
        'name': 'testcluster',
        'description': 'test cluster',
        'user_id': '00000000-0000-0000-0000-000000000000',
        'group_id': None,
        'created': '2021-01-01T01:00:00+00:00',
        'region_id': 1,
        'reservation_expiration': None,
        'lifespan_expiration': None,
        'status': model.ClusterStatus.ACTIVE.value,
        'region_name': 'test',
        'user_name': 'test-user',
        'group_name': None,
        'hosts': [
            {
                'id': 1,
                'cluster_id': 1,
                'fqdn': 'test0.localhost',
                'ipaddr': ['127.0.0.1', '::1'],
                'num_vcpus': 2,
                'ram_mb': 4096,
                'num_volumes': 1,
                'volumes_gb': 20,
            },
            {
                'id': 2,
                'cluster_id': 1,
                'fqdn': 'test1.localhost',
                'ipaddr': ['127.0.0.1', '::1'],
                'num_vcpus': 2,
                'ram_mb': 4096,
                'num_volumes': 1,
                'volumes_gb': 20,
            }
        ],
        'quota': {
            'num_vcpus': 20,
            'ram_mb': 20000,
            'num_volumes': 2,
            'volumes_gb': 200,
        },
        'quota_usage': {
            'num_vcpus': 4,
            'ram_mb': 8192,
            'num_volumes': 2,
            'volumes_gb': 40,
        },
        'product_id': 1,
        'product_name': 'dummy',
        'product_params': {},
        'shared': False,
    }


def test_create_cluster(client, keycloak_mock, db_session_mock, mocker):
    user_id = '00000000-0000-0000-0000-000000000000'
    model.Region.query.get.return_value = region = _create_test_region()
    model.Product.query.get.return_value = product = _create_test_product()
    keycloak_mock.user_list.return_value = []
    keycloak_mock.user_get.return_value = {'id': user_id, 'username': 'test-user'}
    cluster_data = {
        'name': 'testcluster',
        'description': 'test cluster',
        'region_id': 1,
        'reservation_expiration': datetime.datetime(2100, 1, 1, 0, 0, tzinfo=tzutc()),
        'lifespan_expiration': None,
        'product_id': 1,
        'product_params': {},
    }

    model.Cluster.query.filter.return_value.count.return_value = 0

    def db_add(row):
        row.id = 1
        if isinstance(row, model.Cluster):
            mocker.patch.object(model.Cluster, 'region', region)
            mocker.patch.object(model.Cluster, 'product', product)

    db_session_mock.add.side_effect = db_add

    mocker.patch.object(model.Region, 'tower')
    mocker.patch.object(model.Region.tower.Server, 'create_tower_client')
    model.Region.tower.create_tower_client.return_value = (
        tower_client_mock := mocker.Mock()
    )

    tower_client_mock.template_get.return_value = {'id': 123, 'name': 'dummy-create'}
    tower_client_mock.template_launch.return_value = {'id': 321}

    rv = client.post(
        f'{API_BASE}/lab/cluster',
        headers={'Authorization': 'Bearer foobar'},
        json=cluster_data,
    )

    assert rv.status_code == 200, rv.data

    region.tower.create_tower_client.assert_called()
    tower_client_mock.template_get.assert_called_with(template_name='dummy-create')
    tower_client_mock.template_launch.assert_called_with(123, {
        'extra_vars': {
            'rhub_cluster_id': 1,
            'rhub_cluster_name': 'testcluster',
            'rhub_product_id': product.id,
            'rhub_product_name': product.name,
            'rhub_region_id': region.id,
            'rhub_region_name': region.name,
            'rhub_user_id': user_id,
            'rhub_user_name': 'test-user',
        },
    })

    db_session_mock.add.assert_called()
    db_session_mock.commit.assert_called()

    cluster = db_session_mock.add.call_args_list[0].args[0]
    for k, v in cluster_data.items():
        assert getattr(cluster, k) == v

    cluster_event = db_session_mock.add.call_args_list[1].args[0]
    assert cluster_event.cluster_id == 1
    assert cluster_event.tower_job_id == 321

    assert rv.json['user_id'] == '00000000-0000-0000-0000-000000000000'
    assert rv.json['status'] is None
    assert rv.json['created'] == '2021-01-01T01:00:00+00:00'


def test_create_cluster_shared(client, keycloak_mock, db_session_mock, mocker):
    user_id = '00000000-0000-0000-0000-000000000000'
    group_id = '00000000-0000-0000-0000-000000000000'

    model.Region.query.get.return_value = region = _create_test_region()
    model.Product.query.get.return_value = product = _create_test_product()

    keycloak_mock.user_list.return_value = []
    keycloak_mock.user_get.return_value = {
        'id': user_id, 'username': SHAREDCLUSTER_USER,
    }

    sharedcluster_group = {'id': group_id, 'name': SHAREDCLUSTER_GROUP}
    keycloak_mock.group_get.return_value = sharedcluster_group
    keycloak_mock.group_list.return_value = [sharedcluster_group]

    cluster_data = {
        'name': 'testsharedcluster',
        'description': 'test shared cluster',
        'region_id': 1,
        'product_id': 1,
        'product_params': {},
    }

    model.Cluster.query.filter.return_value.count.return_value = 0

    def db_add(row):
        row.id = 1
        if isinstance(row, model.Cluster):
            mocker.patch.object(model.Cluster, 'region', region)
            mocker.patch.object(model.Cluster, 'product', product)

    db_session_mock.add.side_effect = db_add

    mocker.patch.object(model.Region, 'tower')
    mocker.patch.object(model.Region.tower.Server, 'create_tower_client')
    model.Region.tower.create_tower_client.return_value = (
        tower_client_mock := mocker.Mock()
    )

    tower_client_mock.template_get.return_value = {'id': 123, 'name': 'dummy-create'}
    tower_client_mock.template_launch.return_value = {'id': 321}

    rv = client.post(
        f'{API_BASE}/lab/cluster',
        headers={'Authorization': 'Bearer foobar'},
        json=cluster_data | {'shared': True},
    )

    assert rv.status_code == 200, rv.data

    region.tower.create_tower_client.assert_called()
    tower_client_mock.template_get.assert_called_with(template_name='dummy-create')
    tower_client_mock.template_launch.assert_called_with(123, {
        'extra_vars': {
            'rhub_cluster_id': 1,
            'rhub_cluster_name': 'testsharedcluster',
            'rhub_product_id': product.id,
            'rhub_product_name': product.name,
            'rhub_region_id': region.id,
            'rhub_region_name': region.name,
            'rhub_user_id': user_id,
            'rhub_user_name': SHAREDCLUSTER_USER,
        },
    })

    db_session_mock.add.assert_called()
    db_session_mock.commit.assert_called()

    cluster = db_session_mock.add.call_args_list[0].args[0]
    for k, v in cluster_data.items():
        assert getattr(cluster, k) == v

    cluster_event = db_session_mock.add.call_args_list[1].args[0]
    assert cluster_event.cluster_id == 1
    assert cluster_event.tower_job_id == 321

    assert rv.json['user_id'] == user_id
    assert rv.json['group_id'] == user_id

    assert rv.json['shared'] is True
    assert rv.json['reservation_expiration'] is None
    assert rv.json['lifespan_expiration'] is None


def test_create_cluster_in_disabled_region(client, db_session_mock):
    region = _create_test_region()
    region.enabled = False
    model.Region.query.get.return_value = region
    model.Cluster.query.filter.return_value.count.return_value = 0

    cluster_data = {
        'name': 'testcluster',
        'region_id': 1,
        'reservation_expiration': datetime.datetime(2100, 1, 1, 0, 0, tzinfo=tzutc()),
        'product_id': 1,
        'product_params': {},
    }

    rv = client.post(
        f'{API_BASE}/lab/cluster',
        headers={'Authorization': 'Bearer foobar'},
        json=cluster_data,
    )

    assert rv.status_code == 403


@pytest.mark.parametrize(
    'cluster_name',
    [
        pytest.param('abcd', id='short'),
        pytest.param('abcd' * 10, id='long'),
        pytest.param('ab-cd', id='invalid-characters'),
        pytest.param('localhost'),
        pytest.param('all'),
    ]
)
def test_create_cluster_invalid_name(client, cluster_name):
    region = _create_test_region()
    model.Region.query.get.return_value = region
    model.Cluster.query.filter.return_value.count.return_value = 0

    rv = client.post(
        f'{API_BASE}/lab/cluster',
        headers={'Authorization': 'Bearer foobar'},
        json={
            'name': cluster_name,
            'region_id': 1,
            'reservation_expiration': datetime.datetime(2100, 1, 1, 0, 0, tzinfo=tzutc()),
            'product_id': 1,
            'product_params': {},
        },
    )

    assert rv.status_code == 400


def test_create_cluster_exceeded_reservation(client):
    region = _create_test_region()
    region.reservation_expiration_max = 1
    model.Region.query.get.return_value = region
    model.Cluster.query.filter.return_value.count.return_value = 0

    rv = client.post(
        f'{API_BASE}/lab/cluster',
        headers={'Authorization': 'Bearer foobar'},
        json={
            'name': 'testcluster',
            'region_id': 1,
            'reservation_expiration': '3000-01-01T00:00:00Z',
            'product_id': 1,
            'product_params': {},
        },
    )

    assert rv.status_code == 403
    assert rv.json['detail'] == 'Exceeded maximal reservation time.'


def test_create_cluster_set_lifespan_forbidden(client, mocker):
    mocker.patch('rhub.api.lab.cluster._user_can_set_lifespan').return_value = False

    region = _create_test_region()
    region.lifespan_length = 30
    model.Region.query.get.return_value = region
    model.Cluster.query.filter.return_value.count.return_value = 0

    rv = client.post(
        f'{API_BASE}/lab/cluster',
        headers={'Authorization': 'Bearer foobar'},
        json={
            'name': 'testcluster',
            'region_id': 1,
            'reservation_expiration': '2100-01-01T00:00:00Z',
            'lifespan_expiration': '2100-01-01T00:00:00Z',
            'product_id': 1,
            'product_params': {},
        },
    )

    assert rv.status_code == 403


def test_update_cluster(client, keycloak_mock, db_session_mock):
    region = _create_test_region()
    product = _create_test_product()
    user_id = '00000000-0000-0000-0000-000000000000'
    keycloak_mock.user_get.return_value = {'id': user_id, 'username': 'test-user'}
    keycloak_mock.group_get.return_value = {'id': None, 'name': 'None'}
    cluster = model.Cluster(
        id=1,
        name='testcluster',
        description='test cluster',
        user_id='00000000-0000-0000-0000-000000000000',
        group_id=None,
        created=datetime.datetime(2021, 1, 1, 1, 0, 0, tzinfo=tzutc()),
        region_id=region.id,
        region=region,
        reservation_expiration=None,
        lifespan_expiration=None,
        status=model.ClusterStatus.ACTIVE,
        product_id=1,
        product_params={},
        product=product,
    )
    model.Cluster.query.get.return_value = cluster

    rv = client.patch(
        f'{API_BASE}/lab/cluster/1',
        headers={'Authorization': 'Bearer foobar'},
        json={
            'description': 'test change',
            'group_id': '00000001-0002-0003-0004-000000000000',
        },
    )

    assert rv.status_code == 200

    db_session_mock.commit.assert_called()

    assert cluster.description == 'test change'
    assert cluster.group_id == '00000001-0002-0003-0004-000000000000'


@pytest.mark.parametrize(
    'cluster_data',
    [
        pytest.param({'name': 'newclustername'}, id='name'),
        pytest.param({'region_id': 2}, id='region'),
    ],
)
def test_update_cluster_ro_field(client, cluster_data):
    region = _create_test_region()
    product = _create_test_product()
    cluster = model.Cluster(
        id=1,
        name='testcluster',
        description='test cluster',
        user_id='00000000-0000-0000-0000-000000000000',
        group_id=None,
        created=datetime.datetime(2021, 1, 1, 1, 0, 0, tzinfo=tzutc()),
        region_id=region.id,
        region=region,
        reservation_expiration=None,
        lifespan_expiration=None,
        status=model.ClusterStatus.ACTIVE,
        product_id=1,
        product_params={},
        product=product,
    )
    model.Cluster.query.get.return_value = cluster

    rv = client.patch(
        f'{API_BASE}/lab/cluster/1',
        headers={'Authorization': 'Bearer foobar'},
        json=cluster_data,
    )

    assert rv.status_code == 400


def test_update_cluster_reservation(client, keycloak_mock):
    user_id = '00000000-0000-0000-0000-000000000000'
    keycloak_mock.user_get.return_value = {'id': user_id, 'username': 'test-user'}
    region = _create_test_region()
    product = _create_test_product()
    cluster = model.Cluster(
        id=1,
        name='testcluster',
        description='test cluster',
        user_id='00000000-0000-0000-0000-000000000000',
        group_id=None,
        created=datetime.datetime(2021, 1, 1, 1, 0, 0, tzinfo=tzutc()),
        region_id=region.id,
        region=region,
        reservation_expiration=None,
        lifespan_expiration=None,
        status=model.ClusterStatus.ACTIVE,
        product_id=1,
        product_params={},
        product=product,
    )
    model.Cluster.query.get.return_value = cluster

    new_expiration = datetime.datetime(2100, 1, 1, 0, 0, tzinfo=tzutc())

    rv = client.patch(
        f'{API_BASE}/lab/cluster/1',
        headers={'Authorization': 'Bearer foobar'},
        json={
            'reservation_expiration': new_expiration,
        },
    )

    assert rv.status_code == 200
    assert cluster.reservation_expiration == new_expiration


def test_update_cluster_exceeded_reservation(client):
    region = _create_test_region()
    region.reservation_expiration_max = 1
    product = _create_test_product()
    cluster = model.Cluster(
        id=1,
        name='testcluster',
        description='test cluster',
        user_id='00000000-0000-0000-0000-000000000000',
        group_id=None,
        created=datetime.datetime(2021, 1, 1, 1, 0, 0, tzinfo=tzutc()),
        region_id=region.id,
        region=region,
        reservation_expiration=None,
        lifespan_expiration=None,
        status=model.ClusterStatus.ACTIVE,
        product_id=1,
        product_params={},
        product=product,
    )
    model.Cluster.query.get.return_value = cluster

    new_expiration = datetime.datetime(2100, 1, 1, 0, 0, tzinfo=tzutc())

    rv = client.patch(
        f'{API_BASE}/lab/cluster/1',
        headers={'Authorization': 'Bearer foobar'},
        json={
            'reservation_expiration': new_expiration,
        },
    )

    assert rv.status_code == 403
    assert rv.json['detail'] == 'Exceeded maximal reservation time.'


def test_update_cluster_set_lifespan_forbidden(client, mocker):
    mocker.patch('rhub.api.lab.cluster._user_can_set_lifespan').return_value = False

    region = _create_test_region()
    region.lifespan_length = 30
    product = _create_test_product()
    cluster = model.Cluster(
        id=1,
        name='testcluster',
        description='test cluster',
        user_id='00000000-0000-0000-0000-000000000000',
        group_id=None,
        created=datetime.datetime(2021, 1, 1, 1, 0, 0, tzinfo=tzutc()),
        region_id=region.id,
        region=region,
        reservation_expiration=None,
        lifespan_expiration=None,
        status=model.ClusterStatus.ACTIVE,
        product_id=1,
        product_params={},
        product=product,
    )
    model.Cluster.query.get.return_value = cluster

    rv = client.patch(
        f'{API_BASE}/lab/cluster/1',
        headers={'Authorization': 'Bearer foobar'},
        json={
            'lifespan_expiration': '2100-01-01T00:00:00Z',
        },
    )

    assert rv.status_code == 403


def test_delete_cluster(client, db_session_mock, keycloak_mock, mocker):
    region = _create_test_region()
    product = _create_test_product()
    cluster = model.Cluster(
        id=1,
        name='testcluster',
        description='test cluster',
        user_id='00000000-0000-0000-0000-000000000000',
        group_id=None,
        created=datetime.datetime(2021, 1, 1, 1, 0, 0, tzinfo=tzutc()),
        region_id=region.id,
        region=region,
        reservation_expiration=None,
        lifespan_expiration=None,
        status=model.ClusterStatus.ACTIVE,
        product_id=product.id,
        product_params={},
        product=product,
    )
    model.Cluster.query.get.return_value = cluster

    keycloak_mock.user_get.return_value = {'username': 'test-user'}

    mocker.patch.object(cluster.region, 'tower')
    mocker.patch.object(cluster.region.tower, 'create_tower_client')
    cluster.region.tower.create_tower_client.return_value = (
        tower_client_mock := mocker.Mock(name='foo')
    )

    tower_client_mock.template_get.return_value = {'id': 123, 'name': 'dummy-delete'}
    tower_client_mock.template_launch.return_value = {'id': 321}

    rv = client.delete(
        f'{API_BASE}/lab/cluster/1',
        headers={'Authorization': 'Bearer foobar'},
    )

    assert rv.status_code == 204

    region.tower.create_tower_client.assert_called()
    tower_client_mock.template_get.assert_called_with(template_name='dummy-delete')
    tower_client_mock.template_launch.assert_called_with(123, {
        'extra_vars': {
            'rhub_cluster_id': 1,
            'rhub_cluster_name': 'testcluster',
            'rhub_product_id': product.id,
            'rhub_product_name': product.name,
            'rhub_region_id': region.id,
            'rhub_region_name': region.name,
            'rhub_user_id': cluster.user_id,
            'rhub_user_name': 'test-user',
        },
    })

    db_session_mock.delete.assert_called_with(cluster)
    db_session_mock.commit.assert_called()


def test_get_cluster_events(client):
    events = [
        model.ClusterTowerJobEvent(
            id=1,
            date=datetime.datetime(2021, 1, 1, 1, 0, 0, tzinfo=tzutc()),
            user_id='00000000-0000-0000-0000-000000000000',
            cluster_id=1,
            tower_id=1,
            tower_job_id=1,
            status=model.ClusterStatus.POST_PROVISIONING,
        ),
        model.ClusterReservationChangeEvent(
            id=2,
            date=datetime.datetime(2021, 1, 1, 2, 0, 0, tzinfo=tzutc()),
            user_id='00000000-0000-0000-0000-000000000000',
            cluster_id=1,
            old_value=None,
            new_value=datetime.datetime(2021, 2, 1, 0, 0, 0, tzinfo=tzutc()),
        ),
    ]
    cluster = model.Cluster(
        id=1,
        name='testcluster',
        description='test cluster',
        user_id='00000000-0000-0000-0000-000000000000',
        group_id=None,
        created=datetime.datetime(2021, 1, 1, 1, 0, 0, tzinfo=tzutc()),
        region_id=1,
        reservation_expiration=None,
        lifespan_expiration=None,
        status=model.ClusterStatus.ACTIVE,
        events=events,
    )
    model.Cluster.query.get.return_value = cluster

    rv = client.get(
        f'{API_BASE}/lab/cluster/1/events',
        headers={'Authorization': 'Bearer foobar'},
    )

    assert rv.status_code == 200

    model.Cluster.query.get.assert_called_with(1)

    assert rv.json == [
        {
            'id': 1,
            'type': model.ClusterEventType.TOWER_JOB.value,
            'cluster_id': 1,
            'date': '2021-01-01T01:00:00+00:00',
            'user_id': '00000000-0000-0000-0000-000000000000',
            'tower_id': 1,
            'tower_job_id': 1,
            'status': model.ClusterStatus.POST_PROVISIONING.value,
        },
        {
            'id': 2,
            'type': model.ClusterEventType.RESERVATION_CHANGE.value,
            'cluster_id': 1,
            'date': '2021-01-01T02:00:00+00:00',
            'user_id': '00000000-0000-0000-0000-000000000000',
            'old_value': None,
            'new_value': '2021-02-01T00:00:00+00:00',
        },
    ]


def test_get_cluster_hosts(client):
    model.Cluster.query.get.return_value = model.Cluster(
        id=1,
        name='testcluster',
        description='test cluster',
        user_id='00000000-0000-0000-0000-000000000000',
        group_id=None,
        created=datetime.datetime(2021, 1, 1, 1, 0, 0, tzinfo=tzutc()),
        region_id=1,
        reservation_expiration=None,
        lifespan_expiration=None,
        status=model.ClusterStatus.ACTIVE,
        hosts=[
            model.ClusterHost(
                id=1,
                cluster_id=1,
                fqdn='host0.example.com',
                ipaddr=['1.2.3.4'],
                num_vcpus=2,
                ram_mb=2048,
                num_volumes=3,
                volumes_gb=30,
            ),
            model.ClusterHost(
                id=2,
                cluster_id=1,
                fqdn='host1.example.com',
                ipaddr=['1:2::3:4'],
                num_vcpus=2,
                ram_mb=2048,
                num_volumes=3,
                volumes_gb=30,
            ),
        ],
    )

    rv = client.get(
        f'{API_BASE}/lab/cluster/1/hosts',
        headers={'Authorization': 'Bearer foobar'},
    )

    assert rv.status_code == 200

    model.Cluster.query.get.assert_called_with(1)

    assert rv.json == [
        {
            'id': 1,
            'cluster_id': 1,
            'fqdn': 'host0.example.com',
            'ipaddr': ['1.2.3.4'],
            'num_vcpus': 2,
            'ram_mb': 2048,
            'num_volumes': 3,
            'volumes_gb': 30,
        },
        {
            'id': 2,
            'cluster_id': 1,
            'fqdn': 'host1.example.com',
            'ipaddr': ['1:2::3:4'],
            'num_vcpus': 2,
            'ram_mb': 2048,
            'num_volumes': 3,
            'volumes_gb': 30,
        },
    ]


def test_create_cluster_hosts(client, db_session_mock):
    model.Cluster.query.get.return_value = model.Cluster(
        id=1,
        name='testcluster',
        description='test cluster',
        user_id='00000000-0000-0000-0000-000000000000',
        group_id=None,
        created=datetime.datetime(2021, 1, 1, 1, 0, 0, tzinfo=tzutc()),
        region_id=1,
        reservation_expiration=None,
        lifespan_expiration=None,
        status=model.ClusterStatus.ACTIVE,
    )
    hosts_data = [
        {
            'fqdn': 'host0.example.com',
            'ipaddr': ['1.2.3.4'],
            'num_vcpus': 2,
            'ram_mb': 2048,
            'num_volumes': 3,
            'volumes_gb': 30,
        },
        {
            'fqdn': 'host1.example.com',
            'ipaddr': ['1:2::3:4'],
            'num_vcpus': 2,
            'ram_mb': 2048,
            'num_volumes': 3,
            'volumes_gb': 30,
        },
    ]

    rv = client.post(
        f'{API_BASE}/lab/cluster/1/hosts',
        headers={'Authorization': 'Bearer foobar'},
        json=hosts_data,
    )

    assert rv.status_code == 200

    db_session_mock.add_all.assert_called()
    db_session_mock.commit.assert_called()

    hosts = db_session_mock.add_all.call_args.args[0]
    for host_data, host_row in zip(hosts_data, hosts):
        for k, v in host_data.items():
            assert getattr(host_row, k) == v


def test_delete_cluster_hosts(client, db_session_mock):
    hosts = [
        model.ClusterHost(
            id=1,
            cluster_id=1,
            fqdn='host0.example.com',
            ipaddr=['1.2.3.4'],
        ),
        model.ClusterHost(
            id=2,
            cluster_id=1,
            fqdn='host1.example.com',
            ipaddr=['1:2::3:4'],
        ),
    ]
    cluster = model.Cluster(
        id=1,
        name='testcluster',
        description='test cluster',
        user_id='00000000-0000-0000-0000-000000000000',
        group_id=None,
        created=datetime.datetime(2021, 1, 1, 1, 0, 0, tzinfo=tzutc()),
        region_id=1,
        reservation_expiration=None,
        lifespan_expiration=None,
        status=model.ClusterStatus.ACTIVE,
        hosts=hosts,
    )
    model.Cluster.query.get.return_value = cluster

    rv = client.delete(
        f'{API_BASE}/lab/cluster/1/hosts',
        headers={'Authorization': 'Bearer foobar'},
    )

    assert rv.status_code == 204

    for host in hosts:
        db_session_mock.delete.assert_any_call(host)
    db_session_mock.commit.assert_called()
