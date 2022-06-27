import datetime
from unittest.mock import ANY

import pytest
from dateutil.tz import tzutc

from rhub.lab import SHAREDCLUSTER_GROUP, SHAREDCLUSTER_USER, model
from rhub.openstack import model as openstack_model
from rhub.tower import model as tower_model


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
        reservation_expiration_max=None,
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
    )


def _create_test_project():
    return openstack_model.Project(
        id=1,
        cloud_id=1,
        cloud=openstack_model.Cloud(
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
        name='test_project',
        description='',
        owner_id='00000000-0000-0000-0000-000000000000',
        group_id='00000000-0000-0000-0000-000000000001',
    )


@pytest.fixture
def project(mocker):
    mocker.patch.object(openstack_model.Cloud, 'owner_group_name', 'cloudowner')
    mocker.patch.object(openstack_model.Project, 'owner_name', 'projectowner')
    mocker.patch.object(openstack_model.Project, 'group_name', 'projectgroup')

    p = _create_test_project()

    openstack_model.Project.query.get.return_value = p

    query = openstack_model.Project.query.filter.return_value
    query.count.return_value = 1
    query.first.return_value = p

    yield p


@pytest.fixture
def shared_project(mocker):
    mocker.patch.object(openstack_model.Cloud, 'owner_group_name', 'cloudowner')
    mocker.patch.object(openstack_model.Project, 'owner_name', SHAREDCLUSTER_USER)
    mocker.patch.object(openstack_model.Project, 'group_name', SHAREDCLUSTER_GROUP)

    p = _create_test_project()
    p.owner_id = 'ffffffff-0000-0000-0000-000000000000'
    p.group_id = 'ffffffff-0000-0000-0000-000000000001'

    openstack_model.Project.query.get.return_value = p

    query = openstack_model.Project.query.filter.return_value
    query.count.return_value = 1
    query.first.return_value = p

    yield p


@pytest.fixture(autouse=True)
def _get_sharedcluster_user_id(mocker, shared_project):
    m = mocker.patch('rhub.api.lab.cluster._get_sharedcluster_user_id')
    m.return_value = shared_project.owner_id
    yield m


@pytest.fixture(autouse=True)
def _get_sharedcluster_group_id(mocker, shared_project):
    m = mocker.patch('rhub.api.lab.cluster._get_sharedcluster_group_id')
    m.return_value = shared_project.group_id
    yield m


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


def test_list_clusters(client, keycloak_mock, mocker, project):
    sample_region = _create_test_region()
    sample_product = _create_test_product()

    model.Cluster.query.filter.return_value.limit.return_value.offset.return_value = [
        model.Cluster(
            id=1,
            name='testcluster',
            description='test cluster',
            created=datetime.datetime(2021, 1, 1, 1, 0, 0, tzinfo=tzutc()),
            region_id=1,
            region=sample_region,
            project_id=1,
            project=project,
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
    model.Cluster.query.filter.return_value.count.return_value = 1

    rv = client.get(
        f'{API_BASE}/lab/cluster',
        headers={'Authorization': 'Bearer foobar'},
    )

    assert rv.status_code == 200, rv.data
    assert rv.json == {
        'data': [
            {
                'id': 1,
                'name': 'testcluster',
                'description': 'test cluster',
                'owner_id': project.owner_id,
                'owner_name': project.owner_name,
                'group_id': project.group_id,
                'group_name': project.group_name,
                'created': '2021-01-01T01:00:00+00:00',
                'region_id': 1,
                'project_id': 1,
                'reservation_expiration': None,
                'lifespan_expiration': None,
                'status': model.ClusterStatus.ACTIVE.value,
                'status_flag': model.ClusterStatus.ACTIVE.flag,
                'region_name': 'test',
                'hosts': [],
                'quota': None,
                'quota_usage': None,
                'product_id': 1,
                'product_name': 'dummy',
                'product_params': {},
                'shared': False,
                '_href': ANY,
            },
        ],
        'total': 1,
    }


def test_get_cluster(client, keycloak_mock, mocker, project):
    sample_region = _create_test_region()
    sample_product = _create_test_product()

    model.Cluster.query.get.return_value = model.Cluster(
        id=1,
        name='testcluster',
        description='test cluster',
        created=datetime.datetime(2021, 1, 1, 1, 0, 0, tzinfo=tzutc()),
        region_id=1,
        region=sample_region,
        project_id=1,
        project=project,
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

    assert rv.json == {
        'id': 1,
        'name': 'testcluster',
        'description': 'test cluster',
        'owner_id': project.owner_id,
        'owner_name': project.owner_name,
        'group_id': project.group_id,
        'group_name': project.group_name,
        'created': '2021-01-01T01:00:00+00:00',
        'region_id': 1,
        'project_id': 1,
        'reservation_expiration': None,
        'lifespan_expiration': None,
        'status': model.ClusterStatus.ACTIVE.value,
        'status_flag': model.ClusterStatus.ACTIVE.flag,
        'region_name': 'test',
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
        '_href': ANY,
    }


def test_create_cluster(client, keycloak_mock, db_session_mock, mocker, project):
    model.Region.query.get.return_value = region = _create_test_region()
    model.Product.query.get.return_value = product = _create_test_product()

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
            mocker.patch.object(model.Cluster, 'project', project)

    db_session_mock.add.side_effect = db_add

    mocker.patch.object(model.Region, 'tower')
    mocker.patch.object(model.Region.tower.Server, 'create_tower_client')
    model.Region.tower.create_tower_client.return_value = (
        tower_client_mock := mocker.Mock()
    )

    mocker.patch.object(model.Region, 'is_product_enabled').return_value = True

    tower_client_mock.template_get.return_value = {'id': 123, 'name': 'dummy-create'}
    tower_client_mock.template_launch.return_value = {'id': 321}

    mocker.patch('rhub.api.lab.cluster._cluster_href').return_value = {}

    keycloak_mock.user_get.return_value = {'username': project.owner_name}

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
            'rhub_project_id': project.id,
            'rhub_project_name': project.name,
            'rhub_user_id': project.owner_id,
            'rhub_user_name': project.owner_name,
        },
    })

    db_session_mock.add.assert_called()
    db_session_mock.commit.assert_called()

    cluster = db_session_mock.add.call_args_list[0].args[0]
    for k, v in cluster_data.items():
        assert getattr(cluster, k) == v, k

    cluster_event = db_session_mock.add.call_args_list[1].args[0]
    assert cluster_event.cluster_id == 1
    assert cluster_event.tower_job_id == 321

    assert rv.json['owner_id'] == project.owner_id
    assert rv.json['status'] == model.ClusterStatus.QUEUED.value
    assert rv.json['created'] == '2021-01-01T01:00:00+00:00'


def test_create_cluster_shared(client, keycloak_mock, db_session_mock, mocker,
                               shared_project):
    model.Region.query.get.return_value = region = _create_test_region()
    model.Product.query.get.return_value = product = _create_test_product()

    mocker.patch.object(model.Region, 'is_product_enabled').return_value = True

    keycloak_mock.user_get.return_value = {'username': shared_project.owner_name}

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
            mocker.patch.object(model.Cluster, 'project', shared_project)

    db_session_mock.add.side_effect = db_add

    mocker.patch.object(model.Region, 'tower')
    mocker.patch.object(model.Region.tower.Server, 'create_tower_client')
    model.Region.tower.create_tower_client.return_value = (
        tower_client_mock := mocker.Mock()
    )

    tower_client_mock.template_get.return_value = {'id': 123, 'name': 'dummy-create'}
    tower_client_mock.template_launch.return_value = {'id': 321}

    mocker.patch('rhub.api.lab.cluster._cluster_href').return_value = {}

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
            'rhub_project_id': shared_project.id,
            'rhub_project_name': shared_project.name,
            'rhub_user_id': shared_project.owner_id,
            'rhub_user_name': shared_project.group_name,
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

    assert rv.json['owner_id'] == shared_project.owner_id
    assert rv.json['group_id'] == shared_project.group_id

    assert rv.json['shared'] is True
    assert rv.json['reservation_expiration'] is None
    assert rv.json['lifespan_expiration'] is None


def test_create_cluster_in_disabled_region(client, db_session_mock, mocker):
    region = _create_test_region()
    region.enabled = False

    model.Region.query.get.return_value = region
    model.Cluster.query.filter.return_value.count.return_value = 0

    project_query = openstack_model.Project.query.filter.return_value
    project_query.count.return_value = 1
    project_query.first.return_value = _create_test_project()

    mocker.patch.object(model.Region, 'is_product_enabled').return_value = True

    mocker.patch('rhub.api.lab.cluster._cluster_href').return_value = {}

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
def test_create_cluster_invalid_name(client, cluster_name, mocker):
    region = _create_test_region()
    model.Region.query.get.return_value = region
    model.Cluster.query.filter.return_value.count.return_value = 0

    project_query = openstack_model.Project.query.filter.return_value
    project_query.count.return_value = 1
    project_query.first.return_value = _create_test_project()

    mocker.patch.object(model.Region, 'is_product_enabled').return_value = True

    mocker.patch('rhub.api.lab.cluster._cluster_href').return_value = {}

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


def test_create_cluster_exceeded_reservation(client, mocker):
    region = _create_test_region()
    region.reservation_expiration_max = 1
    model.Region.query.get.return_value = region
    model.Cluster.query.filter.return_value.count.return_value = 0

    project_query = openstack_model.Project.query.filter.return_value
    project_query.count.return_value = 1
    project_query.first.return_value = _create_test_project()

    mocker.patch.object(model.Region, 'is_product_enabled').return_value = True

    mocker.patch('rhub.api.lab.cluster._cluster_href').return_value = {}

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

    project_query = openstack_model.Project.query.filter.return_value
    project_query.count.return_value = 1
    project_query.first.return_value = _create_test_project()

    mocker.patch.object(model.Region, 'is_product_enabled').return_value = True

    mocker.patch('rhub.api.lab.cluster._cluster_href').return_value = {}

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


def test_create_cluster_with_disabled_product(
        client, keycloak_mock, db_session_mock, mocker):
    model.Product.query.get.return_value = product = _create_test_product()
    product.enabled = False

    m = mocker.patch.object(model.Region, 'products_relation')
    model.Region.query.get.return_value = region = _create_test_region()

    project_query = openstack_model.Project.query.filter.return_value
    project_query.count.return_value = 1
    project_query.first.return_value = _create_test_project()

    mocker.patch('rhub.api.lab.cluster._cluster_href').return_value = {}

    region.products_relation.filter.return_value.first.return_value = (
        model.RegionProduct(
            region_id=region.id,
            product_id=product.id,
            enabled=True,
            product=product,
        )
    )

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

    rv = client.post(
        f'{API_BASE}/lab/cluster',
        headers={'Authorization': 'Bearer foobar'},
        json=cluster_data,
    )

    assert rv.status_code == 400, rv.data

    db_session_mock.commit.assert_not_called()


def test_create_cluster_with_disabled_product_in_region(
        client, keycloak_mock, db_session_mock, mocker):
    model.Product.query.get.return_value = product = _create_test_product()
    product.enabled = False

    m = mocker.patch.object(model.Region, 'products_relation')
    model.Region.query.get.return_value = region = _create_test_region()

    project_query = openstack_model.Project.query.filter.return_value
    project_query.count.return_value = 1
    project_query.first.return_value = _create_test_project()

    region.products_relation.filter.return_value.first.return_value = (
        model.RegionProduct(
            region_id=region.id,
            product_id=product.id,
            enabled=True,
            product=product,
        )
    )

    mocker.patch('rhub.api.lab.cluster._cluster_href').return_value = {}

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

    rv = client.post(
        f'{API_BASE}/lab/cluster',
        headers={'Authorization': 'Bearer foobar'},
        json=cluster_data,
    )

    assert rv.status_code == 400, rv.data

    db_session_mock.commit.assert_not_called()


def test_update_cluster(client, keycloak_mock, db_session_mock, mocker, project):
    region = _create_test_region()
    product = _create_test_product()
    cluster = model.Cluster(
        id=1,
        name='testcluster',
        description='test cluster',
        created=datetime.datetime(2021, 1, 1, 1, 0, 0, tzinfo=tzutc()),
        region_id=region.id,
        region=region,
        project_id=project.id,
        project=project,
        reservation_expiration=None,
        lifespan_expiration=None,
        status=model.ClusterStatus.ACTIVE,
        product_id=1,
        product_params={},
        product=product,
    )
    model.Cluster.query.get.return_value = cluster

    mocker.patch('rhub.api.lab.cluster._cluster_href').return_value = {}

    rv = client.patch(
        f'{API_BASE}/lab/cluster/1',
        headers={'Authorization': 'Bearer foobar'},
        json={
            'description': 'test change',
        },
    )

    assert rv.status_code == 200

    db_session_mock.commit.assert_called()

    assert cluster.description == 'test change'


@pytest.mark.parametrize(
    'cluster_data',
    [
        pytest.param({'name': 'newclustername'}, id='name'),
        pytest.param({'region_id': 2}, id='region'),
    ],
)
def test_update_cluster_ro_field(client, cluster_data, mocker, project):
    region = _create_test_region()
    product = _create_test_product()
    cluster = model.Cluster(
        id=1,
        name='testcluster',
        description='test cluster',
        created=datetime.datetime(2021, 1, 1, 1, 0, 0, tzinfo=tzutc()),
        region_id=region.id,
        region=region,
        project_id=project.id,
        project=project,
        reservation_expiration=None,
        lifespan_expiration=None,
        status=model.ClusterStatus.ACTIVE,
        product_id=1,
        product_params={},
        product=product,
    )
    model.Cluster.query.get.return_value = cluster

    mocker.patch('rhub.api.lab.cluster._cluster_href').return_value = {}

    rv = client.patch(
        f'{API_BASE}/lab/cluster/1',
        headers={'Authorization': 'Bearer foobar'},
        json=cluster_data,
    )

    assert rv.status_code == 400


def test_update_cluster_reservation(client, keycloak_mock, db_session_mock, mocker,
                                    project):
    region = _create_test_region()
    product = _create_test_product()

    old_expiration = datetime.datetime(2100, 1, 1, 0, 0, tzinfo=tzutc())
    new_expiration = datetime.datetime(2100, 1, 2, 0, 0, tzinfo=tzutc())

    cluster = model.Cluster(
        id=1,
        name='testcluster',
        description='test cluster',
        created=datetime.datetime(2021, 1, 1, 1, 0, 0, tzinfo=tzutc()),
        region_id=region.id,
        region=region,
        project_id=project.id,
        project=project,
        reservation_expiration=old_expiration,
        lifespan_expiration=None,
        status=model.ClusterStatus.ACTIVE,
        product_id=1,
        product_params={},
        product=product,
    )
    model.Cluster.query.get.return_value = cluster

    mocker.patch('rhub.api.lab.cluster._cluster_href').return_value = {}

    rv = client.patch(
        f'{API_BASE}/lab/cluster/1',
        headers={'Authorization': 'Bearer foobar'},
        json={
            'reservation_expiration': new_expiration,
        },
    )

    assert rv.status_code == 200
    assert cluster.reservation_expiration == new_expiration

    event = db_session_mock.add.call_args_list[0].args[0]
    assert event.type == model.ClusterEventType.RESERVATION_CHANGE
    assert event.old_value == old_expiration
    assert event.new_value == new_expiration


def test_update_cluster_exceeded_reservation(client, mocker, project):
    region = _create_test_region()
    region.reservation_expiration_max = 1
    product = _create_test_product()
    cluster = model.Cluster(
        id=1,
        name='testcluster',
        description='test cluster',
        created=datetime.datetime(2021, 1, 1, 1, 0, 0, tzinfo=tzutc()),
        region_id=region.id,
        region=region,
        project_id=project.id,
        project=project,
        reservation_expiration=None,
        lifespan_expiration=None,
        status=model.ClusterStatus.ACTIVE,
        product_id=1,
        product_params={},
        product=product,
    )
    model.Cluster.query.get.return_value = cluster

    new_expiration = datetime.datetime(2100, 1, 1, 0, 0, tzinfo=tzutc())

    mocker.patch('rhub.api.lab.cluster._cluster_href').return_value = {}

    rv = client.patch(
        f'{API_BASE}/lab/cluster/1',
        headers={'Authorization': 'Bearer foobar'},
        json={
            'reservation_expiration': new_expiration,
        },
    )

    assert rv.status_code == 403
    assert rv.json['detail'] == 'Exceeded maximal reservation time.'


def test_update_cluster_set_lifespan_forbidden(client, mocker, project):
    mocker.patch('rhub.api.lab.cluster._user_can_set_lifespan').return_value = False

    region = _create_test_region()
    region.lifespan_length = 30
    product = _create_test_product()
    cluster = model.Cluster(
        id=1,
        name='testcluster',
        description='test cluster',
        created=datetime.datetime(2021, 1, 1, 1, 0, 0, tzinfo=tzutc()),
        region_id=region.id,
        region=region,
        project_id=project.id,
        project=project,
        reservation_expiration=None,
        lifespan_expiration=None,
        status=model.ClusterStatus.ACTIVE,
        product_id=1,
        product_params={},
        product=product,
    )
    model.Cluster.query.get.return_value = cluster

    mocker.patch('rhub.api.lab.cluster._cluster_href').return_value = {}

    rv = client.patch(
        f'{API_BASE}/lab/cluster/1',
        headers={'Authorization': 'Bearer foobar'},
        json={
            'lifespan_expiration': '2100-01-01T00:00:00Z',
        },
    )

    assert rv.status_code == 403


def test_delete_cluster(client, db_session_mock, keycloak_mock, mocker, project):
    region = _create_test_region()
    product = _create_test_product()
    cluster = model.Cluster(
        id=1,
        name='testcluster',
        description='test cluster',
        created=datetime.datetime(2021, 1, 1, 1, 0, 0, tzinfo=tzutc()),
        region_id=region.id,
        region=region,
        project_id=project.id,
        project=project,
        reservation_expiration=None,
        lifespan_expiration=None,
        status=model.ClusterStatus.ACTIVE,
        product_id=product.id,
        product_params={},
        product=product,
    )
    model.Cluster.query.get.return_value = cluster

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
            'rhub_project_id': project.id,
            'rhub_project_name': project.name,
            'rhub_user_id': project.owner_id,
            'rhub_user_name': project.owner_name,
        },
    })

    # Clusters should not be deleted immediately
    db_session_mock.delete.assert_not_called()
    db_session_mock.commit.assert_called()


def test_get_cluster_events(client, mocker, project):
    mocker.patch.object(model.ClusterTowerJobEvent, 'user_name', 'test-user')
    mocker.patch.object(model.ClusterReservationChangeEvent, 'user_name', 'test-user')

    events = [
        model.ClusterTowerJobEvent(
            id=1,
            date=datetime.datetime(2021, 1, 1, 1, 0, 0, tzinfo=tzutc()),
            user_id='00000000-0000-0000-0000-000000000000',
            cluster_id=1,
            tower_id=1,
            tower=tower_model.Server(id=1),
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
        created=datetime.datetime(2021, 1, 1, 1, 0, 0, tzinfo=tzutc()),
        region_id=1,
        project_id=project.id,
        project=project,
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
            'user_name': 'test-user',
            'tower_id': 1,
            'tower_job_id': 1,
            'status': model.ClusterStatus.POST_PROVISIONING.value,
            '_href': ANY,
        },
        {
            'id': 2,
            'type': model.ClusterEventType.RESERVATION_CHANGE.value,
            'cluster_id': 1,
            'date': '2021-01-01T02:00:00+00:00',
            'user_id': '00000000-0000-0000-0000-000000000000',
            'user_name': 'test-user',
            'old_value': None,
            'new_value': '2021-02-01T00:00:00+00:00',
            '_href': ANY,
        },
    ]


def test_get_cluster_event_stdout(client, mocker):
    event = model.ClusterTowerJobEvent(
        id=1,
        date=datetime.datetime(2021, 1, 1, 1, 0, 0, tzinfo=tzutc()),
        user_id='00000000-0000-0000-0000-000000000000',
        cluster_id=1,
        tower_id=1,
        tower=tower_model.Server(id=1),
        tower_job_id=1,
        status=model.ClusterStatus.POST_PROVISIONING,
    )
    mocker.patch.object(event, 'get_tower_job_output').return_value = 'Ansible output.'

    model.ClusterTowerJobEvent.query.get.return_value = event

    rv = client.get(
        f'{API_BASE}/lab/cluster_event/1/stdout',
        headers={'Authorization': 'Bearer foobar'},
    )

    assert rv.data == b'Ansible output.'


def test_get_cluster_hosts(client, project):
    model.Cluster.query.get.return_value = model.Cluster(
        id=1,
        name='testcluster',
        description='test cluster',
        created=datetime.datetime(2021, 1, 1, 1, 0, 0, tzinfo=tzutc()),
        region_id=1,
        project_id=project.id,
        project=project,
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
            '_href': ANY,
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
            '_href': ANY,
        },
    ]


def test_create_cluster_hosts(client, db_session_mock, project):
    model.Cluster.query.get.return_value = model.Cluster(
        id=1,
        name='testcluster',
        description='test cluster',
        created=datetime.datetime(2021, 1, 1, 1, 0, 0, tzinfo=tzutc()),
        region_id=1,
        project_id=project.id,
        project=project,
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


def test_delete_cluster_hosts(client, db_session_mock, project):
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
        created=datetime.datetime(2021, 1, 1, 1, 0, 0, tzinfo=tzutc()),
        region_id=1,
        project_id=project.id,
        project=project,
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
