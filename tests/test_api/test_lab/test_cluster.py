import datetime

import pytest
from dateutil.tz import tzutc

from rhub.lab import model
from rhub.api.vault import Vault
from rhub.auth.keycloak import KeycloakClient


API_BASE = '/v0'


@pytest.fixture(autouse=True)
def keycloak_mock(mocker):
    keycloak_mock = mocker.Mock(spec=KeycloakClient)

    get_keycloak_mock = mocker.patch(f'rhub.api.lab.cluster.get_keycloak')
    get_keycloak_mock.return_value = keycloak_mock
    mocker.patch(f'rhub.lab.model.get_keycloak').return_value = keycloak_mock
    yield keycloak_mock


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
        quota_id=None,
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


def test_list_clusters(client, keycloak_mock, mocker):
    user_id = '00000000-0000-0000-0000-000000000000'
    sample_region = _create_test_region()
    keycloak_mock.user_get.return_value = {'id': user_id, 'username': 'test-user'}
    model.Cluster.query.all.return_value = [
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
        ),
    ]

    rv = client.get(
        f'{API_BASE}/lab/cluster',
        headers={'Authorization': 'Bearer foobar'},
    )
    keycloak_mock.user_get.assert_called_with(user_id)

    assert rv.status_code == 200
    assert rv.json == [
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
        },
    ]


def test_get_cluster(client, keycloak_mock):
    user_id = '00000000-0000-0000-0000-000000000000'
    sample_region = _create_test_region()
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
    )

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
    }


def test_create_cluster(client, keycloak_mock, db_session_mock):
    user_id = '00000000-0000-0000-0000-000000000000'
    model.Region.query.get.return_value = _create_test_region()
    keycloak_mock.user_get.return_value = {'id': user_id, 'username': 'test-user'}
    cluster_data = {
        'name': 'testcluster',
        'description': 'test cluster',
        'region_id': 1,
        'reservation_expiration': datetime.datetime(2100, 1, 1, 0, 0, tzinfo=tzutc()),
        'lifespan_expiration': None
    }

    db_session_mock.add.side_effect = _db_add_row_side_effect({'id': 1})

    rv = client.post(
        f'{API_BASE}/lab/cluster',
        headers={'Authorization': 'Bearer foobar'},
        json=cluster_data,
    )

    assert rv.status_code == 200

    db_session_mock.add.assert_called()
    db_session_mock.commit.assert_called()

    cluster = db_session_mock.add.call_args.args[0]
    for k, v in cluster_data.items():
        assert getattr(cluster, k) == v

    assert rv.json['user_id'] == '00000000-0000-0000-0000-000000000000'
    assert rv.json['status'] is None
    assert rv.json['created'] == '2021-01-01T01:00:00+00:00'


def test_create_cluster_in_disabled_region(client, db_session_mock):
    region = _create_test_region()
    region.enabled = False
    model.Region.query.get.return_value = region

    cluster_data = {
        'name': 'testcluster',
        'region_id': 1,
        'reservation_expiration': datetime.datetime(2100, 1, 1, 0, 0, tzinfo=tzutc()),
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

    rv = client.post(
        f'{API_BASE}/lab/cluster',
        headers={'Authorization': 'Bearer foobar'},
        json={
            'name': cluster_name,
            'region_id': 1,
            'reservation_expiration': datetime.datetime(2100, 1, 1, 0, 0, tzinfo=tzutc()),
        },
    )

    assert rv.status_code == 400


def test_create_cluster_exceeded_reservation(client):
    region = _create_test_region()
    region.reservation_expiration_max = 1
    model.Region.query.get.return_value = region

    rv = client.post(
        f'{API_BASE}/lab/cluster',
        headers={'Authorization': 'Bearer foobar'},
        json={
            'name': 'testcluster',
            'region_id': 1,
            'reservation_expiration': '3000-01-01T00:00:00Z',
        },
    )

    assert rv.status_code == 403
    assert rv.json['detail'] == 'Exceeded maximal reservation time.'


def test_create_cluster_set_lifespan_forbidden(client, mocker):
    mocker.patch('rhub.api.lab.cluster._user_can_set_lifespan').return_value = False

    region = _create_test_region()
    region.lifespan_length = 30
    model.Region.query.get.return_value = region

    rv = client.post(
        f'{API_BASE}/lab/cluster',
        headers={'Authorization': 'Bearer foobar'},
        json={
            'name': 'testcluster',
            'region_id': 1,
            'reservation_expiration': '2100-01-01T00:00:00Z',
            'lifespan_expiration': '2100-01-01T00:00:00Z',
        },
    )

    assert rv.status_code == 403


def test_update_cluster(client, keycloak_mock, db_session_mock):
    region = _create_test_region()
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


def test_delete_cluster(client, db_session_mock):
    region = _create_test_region()
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
    )
    model.Cluster.query.get.return_value = cluster

    rv = client.delete(
        f'{API_BASE}/lab/cluster/1',
        headers={'Authorization': 'Bearer foobar'},
        json={
            'description': 'test change',
            'group_id': '00000001-0002-0003-0004-000000000000',
        },
    )

    assert rv.status_code == 204

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
