import base64
import datetime
from unittest.mock import ANY

import pytest
from dateutil.tz import tzutc

from rhub.auth import model as auth_model
from rhub.lab import SHAREDCLUSTER_GROUP, model
from rhub.openstack import model as openstack_model
from rhub.tower import model as tower_model
from rhub.tower.client import TowerError


API_BASE = '/v0'
AUTH_HEADER = {'Authorization': 'Basic X190b2tlbl9fOmR1bW15Cg=='}


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


@pytest.fixture
def auth_user(mocker):
    mocker.patch('rhub.api.lab.cluster._user_can_access_region').return_value = True
    mocker.patch('rhub.api.lab.cluster._user_is_cluster_admin').return_value = True
    mocker.patch('rhub.api.lab.cluster._user_can_access_cluster').return_value = True
    mocker.patch('rhub.api.lab.cluster._user_can_create_reservation').return_value = True
    mocker.patch('rhub.api.lab.cluster._user_can_set_lifespan').return_value = False
    mocker.patch('rhub.api.lab.cluster._user_can_disable_expiration').return_value = False
    mocker.patch('rhub.api.lab.cluster._user_can_create_sharedcluster').return_value = False

    return auth_model.User(
        id=1,
        name='testuser',
        email='testuser@example.com',
    )


@pytest.fixture
def auth_group():
    yield auth_model.Group(
        id=1,
        name='testgroup',
    )


@pytest.fixture
def auth_shared_user(mocker):
    mocker.patch('rhub.api.lab.cluster._user_can_access_region').return_value = True
    mocker.patch('rhub.api.lab.cluster._user_is_cluster_admin').return_value = True
    mocker.patch('rhub.api.lab.cluster._user_can_access_cluster').return_value = True
    mocker.patch('rhub.api.lab.cluster._user_can_create_reservation').return_value = True
    mocker.patch('rhub.api.lab.cluster._user_can_set_lifespan').return_value = True
    mocker.patch('rhub.api.lab.cluster._user_can_disable_expiration').return_value = True
    mocker.patch('rhub.api.lab.cluster._user_can_create_sharedcluster').return_value = True

    yield auth_model.User(
        id=100,
        name='sharedclusters',
        email=f'sharedcluster@example.com',
    )


@pytest.fixture
def auth_shared_group():
    yield auth_model.Group(
        id=100,
        name=SHAREDCLUSTER_GROUP,
    )


@pytest.fixture
def openstack_cloud(mocker, auth_group, di_mock):
    mocker.patch('rhub.openstack.model.di', new=di_mock)
    cloud = openstack_model.Cloud(
        id=1,
        name='test',
        description='',
        owner_group_id=auth_group.id,
        owner_group=auth_group,
        url='https://openstack.example.com:13000',
        credentials='kv/test',
        domain_name='Default',
        domain_id='default',
        networks=['test_net'],
    )
    yield cloud


@pytest.fixture
def region(mocker, auth_group, openstack_cloud):
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
        reservation_expiration_max=None,
        owner_group_id=auth_group.id,
        owner_group=auth_group,
        users_group_id=None,
        users_group=None,
        tower_id=1,
        openstack_id=openstack_cloud.id,
        openstack=openstack_cloud,
    )

    mocker.patch.object(model.Region, 'products_relation')
    mocker.patch.object(model.Region, 'is_product_enabled').return_value = True
    mocker.patch.object(model.Region, 'get_user_quota_usage').return_value = {
        'num_vcpus': 0,
        'ram_mb': 0,
        'num_volumes': 0,
        'volumes_gb': 0,
    }

    model.Region.query.get.return_value = region

    yield region


@pytest.fixture
def region_with_quotas(mocker, auth_group, openstack_cloud):
    quota = model.Quota(
        id=1,
        num_vcpus=1000,
        ram_mb=1000,
        num_volumes=1000,
        volumes_gb=1000,
    )

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
        user_quota_id=quota.id,
        user_quota=quota,
        total_quota_id=quota.id,
        total_quota=quota,
        lifespan_length=None,
        reservations_enabled=True,
        reservation_expiration_max=None,
        owner_group_id=auth_group.id,
        owner_group=auth_group,
        users_group_id=None,
        users_group=None,
        tower_id=1,
        openstack_id=openstack_cloud.id,
        openstack=openstack_cloud,
    )

    mocker.patch.object(model.Region, 'products_relation')
    mocker.patch.object(model.Region, 'is_product_enabled').return_value = True
    mocker.patch.object(model.Region, 'get_user_quota_usage').return_value = {
        'num_vcpus': 0,
        'ram_mb': 0,
        'num_volumes': 0,
        'volumes_gb': 0,
    }

    model.Region.query.get.return_value = region

    yield region


@pytest.fixture
def project(mocker, auth_user, auth_group, openstack_cloud):
    project = openstack_model.Project(
        id=1,
        cloud_id=openstack_cloud.id,
        cloud=openstack_cloud,
        name='test_project',
        description='',
        owner_id=auth_user.id,
        owner=auth_user,
        group_id=auth_group.id,
        group=auth_group,
    )

    openstack_model.Project.query.get.return_value = project

    query = openstack_model.Project.query.filter.return_value
    query.count.return_value = 1
    query.first.return_value = project

    yield project


@pytest.fixture
def shared_project(mocker, auth_shared_user, auth_shared_group, openstack_cloud):
    project = openstack_model.Project(
        id=1,
        cloud_id=openstack_cloud.id,
        cloud=openstack_cloud,
        name='test_project',
        description='',
        owner_id=auth_shared_user.id,
        owner=auth_shared_user,
        group_id=auth_shared_group.id,
        group=auth_shared_group,
    )

    openstack_model.Project.query.get.return_value = project

    query = openstack_model.Project.query.filter.return_value
    query.count.return_value = 1
    query.first.return_value = project

    yield project


@pytest.fixture(autouse=True)
def _get_sharedcluster_group_id(mocker, shared_project):
    m = mocker.patch('rhub.api.lab.cluster._get_sharedcluster_group_id')
    m.return_value = shared_project.group_id
    yield m


@pytest.fixture
def product():
    product = model.Product(
        id=1,
        name='dummy',
        description='dummy',
        enabled=True,
        tower_template_name_create='dummy-create',
        tower_template_name_delete='dummy-delete',
        parameters=[
            {
                'name': 'Node count',
                'variable': 'num_nodes',
                'required': False,
                'type': 'integer',
            },
            {
                'name': 'Node flavor',
                'variable': 'node_flavor',
                'required': False,
                'type': 'string',
            },
        ]
    )

    model.Product.query.get.return_value = product

    yield product


@pytest.fixture
def tower_client(mocker):
    m = mocker.Mock()

    mocker.patch.object(model.Region, 'tower')
    mocker.patch.object(model.Region.tower.Server, 'create_tower_client')
    model.Region.tower.create_tower_client.return_value = m

    yield m


@pytest.fixture(autouse=True)
def _cluster_href(mocker):
    mocker.patch('rhub.api.lab.cluster._cluster_href').return_value = {}


def test_list_clusters(client, mocker, region, project, product):
    q = model.Cluster.query.outerjoin.return_value.filter.return_value
    q.limit.return_value.offset.return_value = [
        model.Cluster(
            id=1,
            name='testcluster',
            description='test cluster',
            created=datetime.datetime(2021, 1, 1, 1, 0, 0, tzinfo=tzutc()),
            region_id=1,
            region=region,
            project_id=1,
            project=project,
            reservation_expiration=None,
            lifespan_expiration=None,
            status=model.ClusterStatus.ACTIVE,
            product_id=1,
            product_params={},
            product=product,
        ),
    ]
    q.count.return_value = 1

    mocker.patch.object(model.Cluster, 'hosts', [])
    mocker.patch.object(model.Cluster, 'quota', None)

    rv = client.get(
        f'{API_BASE}/lab/cluster',
        headers=AUTH_HEADER,
    )

    assert rv.status_code == 200, rv.data
    assert rv.json == {
        'data': [
            {
                'id': 1,
                'name': 'testcluster',
                'description': 'test cluster',
                'owner_id': project.owner_id,
                'owner_name': project.owner.name,
                'group_id': project.group_id,
                'group_name': project.group.name,
                'created': '2021-01-01T01:00:00+00:00',
                'region_id': region.id,
                'region_name': region.name,
                'project_id': project.id,
                'project_name': project.name,
                'reservation_expiration': None,
                'lifespan_expiration': None,
                'status': model.ClusterStatus.ACTIVE.value,
                'status_flag': model.ClusterStatus.ACTIVE.flag,
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


def test_list_clusters_unauthorized(client):
    rv = client.get(
        f'{API_BASE}/lab/cluster',
    )

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


@pytest.mark.parametrize(
    'is_shared', [pytest.param(False, id='personal'), pytest.param(True, id='shared')],
)
@pytest.mark.parametrize(
    'is_admin', [pytest.param(False, id='user'), pytest.param(True, id='admin')],
)
def test_get_cluster(client, mocker, region_with_quotas, project, shared_project,
                     product, is_shared, is_admin):
    if is_shared:
        project = shared_project

    mocker.patch('rhub.api.lab.cluster._user_can_access_cluster').side_effect = (
        lambda cluster, user_id: is_admin or cluster.owner_id == user_id
    )

    region = region_with_quotas

    model.Cluster.query.get.return_value = model.Cluster(
        id=1,
        name='testcluster',
        description='test cluster',
        created=datetime.datetime(2021, 1, 1, 1, 0, 0, tzinfo=tzutc()),
        region_id=1,
        region=region,
        project_id=1,
        project=project,
        reservation_expiration=None,
        lifespan_expiration=None,
        status=model.ClusterStatus.ACTIVE,
        product_id=1,
        product_params={},
        product=product,
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
        model.ClusterHost(
            id=3,
            cluster_id=1,
            fqdn='test2.localhost',
            ipaddr=['127.0.0.1', '::1'],
            num_vcpus=None,
            ram_mb=None,
            num_volumes=None,
            volumes_gb=None,
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
        headers=AUTH_HEADER,
    )

    assert rv.status_code == 200

    model.Cluster.query.get.assert_called_with(1)

    assert rv.json == {
        'id': 1,
        'name': 'testcluster',
        'description': 'test cluster',
        'owner_id': project.owner_id,
        'owner_name': project.owner.name,
        'group_id': project.group_id,
        'group_name': project.group.name,
        'created': '2021-01-01T01:00:00+00:00',
        'region_id': region.id,
        'region_name': region.name,
        'project_id': 1,
        'project_name': project.name,
        'reservation_expiration': None,
        'lifespan_expiration': None,
        'status': model.ClusterStatus.ACTIVE.value,
        'status_flag': model.ClusterStatus.ACTIVE.flag,
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
            },
            {
                'id': 3,
                'cluster_id': 1,
                'fqdn': 'test2.localhost',
                'ipaddr': ['127.0.0.1', '::1'],
                'num_vcpus': None,
                'ram_mb': None,
                'num_volumes': None,
                'volumes_gb': None,
            },
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
        'shared': is_shared,
        '_href': ANY,
    }


def test_get_cluster_forbidden(client, mocker, region, project, product):
    cluster_id = 1

    model.Cluster.query.get.return_value = model.Cluster(
        id=cluster_id,
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

    mocker.patch('rhub.api.lab.cluster._user_can_access_cluster').return_value = False

    rv = client.get(
        f'{API_BASE}/lab/cluster/{cluster_id}',
        headers=AUTH_HEADER,
    )

    model.Cluster.query.get.assert_called_with(cluster_id)

    assert rv.status_code == 403, rv.data
    assert rv.json['title'] == 'Forbidden'
    assert rv.json['detail'] == "You don't have access to this cluster."



def test_get_cluster_non_existent(client):
    cluster_id = 1

    model.Cluster.query.get.return_value = None

    rv = client.get(
        f'{API_BASE}/lab/cluster/{cluster_id}',
        headers=AUTH_HEADER,
    )

    model.Cluster.query.get.assert_called_with(cluster_id)

    assert rv.status_code == 404, rv.data
    assert rv.json['title'] == 'Not Found'
    assert rv.json['detail'] == f'Cluster {cluster_id} does not exist'


def test_get_cluster_unauthorized(client):
    rv = client.get(
        f'{API_BASE}/lab/cluster/1',
    )

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_create_cluster(client, db_session_mock, mocker,
                        region, project, product, tower_client):
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

    tower_client.template_get.return_value = {'id': 123, 'name': 'dummy-create'}
    tower_client.template_launch.return_value = {'id': 321}

    rv = client.post(
        f'{API_BASE}/lab/cluster',
        headers=AUTH_HEADER,
        json=cluster_data,
    )

    assert rv.status_code == 200, rv.data

    region.tower.create_tower_client.assert_called()
    tower_client.template_get.assert_called_with(template_name='dummy-create')
    tower_client.template_launch.assert_called_with(123, {
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
            'rhub_user_name': project.owner.name,
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


def test_create_cluster_shared(client, db_session_mock, mocker,
                               region, shared_project, product, tower_client):
    cluster_data = {
        'name': 'testsharedcluster',
        'description': 'test shared cluster',
        'shared': True,
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

    tower_client.template_get.return_value = {'id': 123, 'name': 'dummy-create'}
    tower_client.template_launch.return_value = {'id': 321}

    rv = client.post(
        f'{API_BASE}/lab/cluster',
        headers=AUTH_HEADER,
        json=cluster_data | {'shared': True},
    )

    assert rv.status_code == 200, rv.data

    region.tower.create_tower_client.assert_called()
    tower_client.template_get.assert_called_with(template_name='dummy-create')
    tower_client.template_launch.assert_called_with(123, {
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
            'rhub_user_name': shared_project.group.name,
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


def test_create_cluster_in_disabled_region(client, db_session_mock, mocker,
                                           region, project):
    region.enabled = False

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
        headers=AUTH_HEADER,
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
def test_create_cluster_invalid_name(client, cluster_name, mocker, region, project):
    model.Cluster.query.filter.return_value.count.return_value = 0

    rv = client.post(
        f'{API_BASE}/lab/cluster',
        headers=AUTH_HEADER,
        json={
            'name': cluster_name,
            'region_id': 1,
            'reservation_expiration': datetime.datetime(2100, 1, 1, 0, 0, tzinfo=tzutc()),
            'product_id': 1,
            'product_params': {},
        },
    )

    assert rv.status_code == 400


def test_create_cluster_exceeded_reservation(client, mocker, region, project):
    region.reservation_expiration_max = 1

    model.Cluster.query.filter.return_value.count.return_value = 0

    rv = client.post(
        f'{API_BASE}/lab/cluster',
        headers=AUTH_HEADER,
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


def test_create_cluster_set_lifespan_forbidden(client, mocker, region, project):
    mocker.patch('rhub.api.lab.cluster._user_can_set_lifespan').return_value = False

    region.lifespan_length = 30

    model.Cluster.query.filter.return_value.count.return_value = 0

    rv = client.post(
        f'{API_BASE}/lab/cluster',
        headers=AUTH_HEADER,
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
        client, db_session_mock, mocker, region, project, product, tower_client):
    product.enabled = False
    region.is_product_enabled.return_value = False

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
        headers=AUTH_HEADER,
        json=cluster_data,
    )

    assert rv.status_code == 400, rv.data

    db_session_mock.commit.assert_not_called()


def test_create_cluster_with_disabled_product_in_region(
        client, db_session_mock, mocker, region, project, product, tower_client):
    product.enabled = False
    region.is_product_enabled.return_value = False

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
        headers=AUTH_HEADER,
        json=cluster_data,
    )

    assert rv.status_code == 400, rv.data

    db_session_mock.commit.assert_not_called()


@pytest.mark.parametrize(
    'num_nodes, exceeded',
    [
        (1, False),
        (2, True),
    ]
)
def test_create_cluster_quota(
        client, db_session_mock, mocker, region, project, product, tower_client,
        num_nodes, exceeded):
    cluster_data = {
        'name': 'testcluster',
        'description': 'test cluster',
        'region_id': 1,
        'reservation_expiration': datetime.datetime(2100, 1, 1, 0, 0, tzinfo=tzutc()),
        'lifespan_expiration': None,
        'product_id': 1,
        'product_params': {
            'num_nodes': num_nodes,
            'node_flavor': 'default',
        },
    }

    model.Cluster.query.filter.return_value.count.return_value = 0

    region_user_quota_id = 1
    region.user_quota = model.Quota(
        id=1,
        num_vcpus=1,
        ram_mb=1024,
        num_volumes=1,
        volumes_gb=10,
    )

    product.flavors = {
        'default': {
            'num_vcpus': 1,
            'ram_mb': 1024,
            'num_volumes': 1,
            'volumes_gb': 10,
        },
    }

    def db_add(row):
        row.id = 1
        if isinstance(row, model.Cluster):
            mocker.patch.object(model.Cluster, 'region', region)
            mocker.patch.object(model.Cluster, 'product', product)
            mocker.patch.object(model.Cluster, 'project', project)

    db_session_mock.add.side_effect = db_add

    tower_client.template_get.return_value = {'id': 123, 'name': 'dummy-create'}
    tower_client.template_launch.return_value = {'id': 321}

    rv = client.post(
        f'{API_BASE}/lab/cluster',
        headers=AUTH_HEADER,
        json=cluster_data,
    )

    if exceeded:
        assert rv.status_code == 400, rv.data
        assert 'Quota Exceeded.' in rv.json['detail']
        assert set(rv.json['exceeded_resources']) == {
            'num_vcpus', 'ram_mb', 'volumes_gb', 'num_volumes'}

    else:
        assert rv.status_code == 200, rv.data


def test_create_cluster_default_expirations(
    client, mocker, db_session_mock, tower_client, region, project, product,
):
    cluster_data = {
        'name': 'testcluster',
        'description': 'Test cluster.',
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
            mocker.patch.object(model.Cluster, 'project', project)

    db_session_mock.add.side_effect = db_add

    tower_client.template_get.return_value = {'id': 123, 'name': 'dummy-create'}
    tower_client.template_launch.return_value = {'id': 321}

    rv = client.post(
        f'{API_BASE}/lab/cluster',
        headers=AUTH_HEADER,
        json=cluster_data,
    )

    assert rv.status_code == 200, rv.data

    db_session_mock.add.assert_called()
    db_session_mock.commit.assert_called()

    cluster = db_session_mock.add.call_args_list[0].args[0]
    assert cluster.reservation_expiration == None
    assert cluster.lifespan_expiration == None


@pytest.mark.parametrize('data_key', ['reservation_expiration', 'lifespan_expiration'])
@pytest.mark.parametrize('data_value', ['', '9999-99-99T99:99:99Z'])
def test_create_cluster_invalid_expirations(
    client, mocker, db_session_mock, tower_client, region, project, product,
    data_key, data_value,
):
    cluster_data = {
        'name': 'testcluster',
        'description': 'Test cluster.',
        'region_id': 1,
        'product_id': 1,
        'product_params': {},
        data_key: data_value,
    }

    region.lifespan_length = 7
    mocker.patch('rhub.api.lab.cluster._user_can_set_lifespan').return_value = True

    model.Cluster.query.filter.return_value.count.return_value = 0

    tower_client.template_get.return_value = {'id': 123, 'name': 'dummy-create'}

    rv = client.post(
        f'{API_BASE}/lab/cluster',
        headers=AUTH_HEADER,
        json=cluster_data,
    )

    assert rv.status_code == 400, rv.data
    assert f"'{data_key}'" in rv.json['detail']

    tower_client.template_launch.assert_not_called()
    db_session_mock.commit.assert_not_called()


def test_create_cluster_existing_name(client, db_session_mock):
    cluster_data = {
        'name': 'testcluster',
        'region_id': 1,
        'product_id': 1,
        'product_params': {},
    }

    model.Cluster.query.filter.return_value.count.return_value = 1

    rv = client.post(
        f'{API_BASE}/lab/cluster',
        headers=AUTH_HEADER,
        json=cluster_data,
    )

    db_session_mock.add.assert_not_called()

    assert rv.status_code == 400, rv.data
    assert rv.json['title'] == 'Bad Request'
    assert rv.json['detail'] == (
        f'Cluster with name {cluster_data["name"]!r} already exists'
    )


@pytest.mark.parametrize(
    'cluster_data, missing_property',
    [
        pytest.param(
            {
                'region_id': 1,
                'product_id': 1,
                'product_params': {},
            },
            'name',
            id='missing_name',
        ),
        pytest.param(
            {
                'name': 'testcluster',
                'product_id': 1,
                'product_params': {},
            },
            'region_id',
            id='missing_region_id',
        ),
        pytest.param(
            {
                'name': 'testcluster',
                'region_id': 1,
                'product_params': {},
            },
            'product_id',
            id='missing_product_id',
        ),
        pytest.param(
            {
                'name': 'testcluster',
                'region_id': 1,
                'product_id': 1,
            },
            'product_params',
            id='missing_product_params',
        ),
    ]
)
def test_create_cluster_missing_properties(
    client,
    db_session_mock,
    cluster_data,
    missing_property
):
    rv = client.post(
        f'{API_BASE}/lab/cluster',
        headers=AUTH_HEADER,
        json=cluster_data,
    )

    db_session_mock.add.assert_not_called()

    assert rv.status_code == 400, rv.data
    assert rv.json['title'] == 'Bad Request'
    assert rv.json['detail'] == f'{missing_property!r} is a required property'


def test_create_cluster_unauthorized(client, db_session_mock):
    cluster_data = {
        'name': 'testcluster',
        'region_id': 1,
        'product_id': 1,
        'product_params': {},
    }

    rv = client.post(
        f'{API_BASE}/lab/cluster',
        json=cluster_data,
    )

    db_session_mock.add.assert_not_called()

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


@pytest.mark.parametrize(
    'is_shared', [pytest.param(False, id='personal'), pytest.param(True, id='shared')],
)
@pytest.mark.parametrize(
    'is_admin', [pytest.param(False, id='user'), pytest.param(True, id='admin')],
)
def test_update_cluster(client, db_session_mock, di_mock, messaging_mock, mocker,
                        region, project, shared_project, product, is_shared, is_admin):
    if is_shared:
        project = shared_project

    mocker.patch('rhub.api.lab.cluster._user_can_access_cluster').side_effect = (
        lambda cluster, user_id: is_admin or cluster.owner_id == user_id
    )

    cluster = model.Cluster(
        id=1,
        name='testcluster',
        description='initial value',
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

    mocker.patch('rhub.api.lab.cluster.di', new=di_mock)

    rv = client.patch(
        f'{API_BASE}/lab/cluster/1',
        headers=AUTH_HEADER,
        json={
            'description': 'changed value',
        },
    )

    if is_shared and not is_admin:
        assert rv.status_code == 403
        assert cluster.description == 'initial value'

        db_session_mock.commit.assert_not_called()

    else:
        assert rv.status_code == 200
        assert cluster.description == 'changed value'

        db_session_mock.commit.assert_called()

        messaging_mock.send.assert_called_with('lab.cluster.update', ANY, extra=ANY)


@pytest.mark.parametrize(
    'cluster_data',
    [
        pytest.param({'name': 'newclustername'}, id='name'),
        pytest.param({'region_id': 2}, id='region'),
    ],
)
def test_update_cluster_ro_field(client, cluster_data, di_mock, messaging_mock, mocker,
                                 region, project, product):
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

    mocker.patch('rhub.api.lab.cluster.di', new=di_mock)

    rv = client.patch(
        f'{API_BASE}/lab/cluster/1',
        headers=AUTH_HEADER,
        json=cluster_data,
    )

    assert rv.status_code == 400

    messaging_mock.send.assert_not_called()


def test_update_cluster_reservation(client, db_session_mock, di_mock, messaging_mock,
                                    mocker, region, project, product):
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

    mocker.patch('rhub.api.lab.cluster.di', new=di_mock)

    rv = client.patch(
        f'{API_BASE}/lab/cluster/1',
        headers=AUTH_HEADER,
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

    messaging_mock.send.assert_called_with('lab.cluster.update', ANY, extra=ANY)


def test_update_cluster_exceeded_reservation(client, di_mock, messaging_mock, mocker,
                                             region, project, product):
    region.reservation_expiration_max = 1

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

    mocker.patch('rhub.api.lab.cluster.di', new=di_mock)

    rv = client.patch(
        f'{API_BASE}/lab/cluster/1',
        headers=AUTH_HEADER,
        json={
            'reservation_expiration': new_expiration,
        },
    )

    assert rv.status_code == 403
    assert rv.json['detail'] == 'Exceeded maximal reservation time.'

    messaging_mock.send.assert_not_called()


def test_update_cluster_set_lifespan_forbidden(
        client, di_mock, messaging_mock, mocker, region, project, product):
    mocker.patch('rhub.api.lab.cluster._user_can_set_lifespan').return_value = False
    mocker.patch('rhub.api.lab.cluster.di', new=di_mock)

    region.lifespan_length = 30

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

    rv = client.patch(
        f'{API_BASE}/lab/cluster/1',
        headers=AUTH_HEADER,
        json={
            'lifespan_expiration': '2100-01-01T00:00:00Z',
        },
    )

    assert rv.status_code == 403

    messaging_mock.send.assert_not_called()


def test_update_cluster_status(client, db_session_mock, di_mock, messaging_mock, mocker,
                               region, project, product):
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
        status=model.ClusterStatus.PROVISIONING,
        product_id=1,
        product_params={},
        product=product,
    )
    model.Cluster.query.get.return_value = cluster

    mocker.patch('rhub.api.lab.cluster.di', new=di_mock)

    rv = client.patch(
        f'{API_BASE}/lab/cluster/1',
        headers=AUTH_HEADER,
        json={
            'status': 'Active',
        },
    )

    assert rv.status_code == 200

    assert len(db_session_mock.add.call_args_list) == 1
    event = db_session_mock.add.call_args_list[0].args[0]
    assert isinstance(event, model.ClusterTowerJobEvent)
    assert event.type == model.ClusterEventType.TOWER_JOB
    assert event.status == model.ClusterStatus.ACTIVE
    assert event.tower_id is None
    assert event.tower_job_id is None

    messaging_mock.send.assert_called_with('lab.cluster.update', ANY, extra=ANY)


def test_update_cluster_extra(client, db_session_mock, di_mock, messaging_mock, mocker,
                              region, project, product):
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
        status=model.ClusterStatus.PROVISIONING,
        product_id=1,
        product_params={},
        product=product,
    )
    model.Cluster.query.get.return_value = cluster

    mocker.patch('rhub.api.lab.cluster.di', new=di_mock)

    rv = client.post(
        f'{API_BASE}/lab/cluster/1/update',
        headers=AUTH_HEADER,
        json={
            'cluster_data': {
                'description': 'foo bar',
                'status': 'Active',
            },
            'tower_job_id': 1234,
        },
    )

    assert rv.status_code == 200

    assert cluster.description == 'foo bar'
    assert cluster.status == model.ClusterStatus.ACTIVE

    assert len(db_session_mock.add.call_args_list) == 1
    event = db_session_mock.add.call_args_list[0].args[0]
    assert isinstance(event, model.ClusterTowerJobEvent)
    assert event.type == model.ClusterEventType.TOWER_JOB
    assert event.status == model.ClusterStatus.ACTIVE
    assert event.tower_id == region.tower_id
    assert event.tower_job_id == 1234

    messaging_mock.send.assert_called_with('lab.cluster.update', ANY, extra=ANY)


@pytest.mark.parametrize('data_key', ['reservation_expiration', 'lifespan_expiration'])
@pytest.mark.parametrize('data_value', ['', '9999-99-99T99:99:99Z'])
def test_update_cluster_invalid_expirations(
    client, mocker, db_session_mock, di_mock, region, project, product,
    data_key, data_value,
):
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

    region.lifespan_length = 7
    mocker.patch('rhub.api.lab.cluster._user_can_set_lifespan').return_value = True
    mocker.patch('rhub.api.lab.cluster.di', new=di_mock)

    rv = client.patch(
        f'{API_BASE}/lab/cluster/1',
        headers=AUTH_HEADER,
        json={
            data_key: data_value
        },
    )

    assert rv.status_code == 400, rv.data
    assert f"'{data_key}'" in rv.json['detail']

    db_session_mock.commit.assert_not_called()


def test_update_cluster_forbidden(client, db_session_mock, mocker):
    cluster_id = 1

    mocker.patch(
        'rhub.api.lab.cluster._user_can_access_cluster',
    ).return_value = False

    rv = client.patch(
        f'{API_BASE}/lab/cluster/{cluster_id}',
        headers=AUTH_HEADER,
        json={
            'description': 'test change',
        },
    )

    model.Cluster.query.get.assert_called_with(cluster_id)

    db_session_mock.commit.assert_not_called

    assert rv.status_code == 403, rv.data
    assert rv.json['title'] == 'Forbidden'
    assert rv.json['detail'] == "You don't have access to this cluster."


def test_update_cluster_non_existent(client, db_session_mock):
    cluster_id = 1

    model.Cluster.query.get.return_value = None

    rv = client.patch(
        f'{API_BASE}/lab/cluster/{cluster_id}',
        headers=AUTH_HEADER,
        json={
            'description': 'test change',
        },
    )

    db_session_mock.commit.assert_not_called()

    assert rv.status_code == 404, rv.data
    assert rv.json['title'] == 'Not Found'
    assert rv.json['detail'] == f'Cluster {cluster_id} does not exist'


def test_update_cluster_unauthorized(client, db_session_mock):
    rv = client.patch(
        f'{API_BASE}/lab/cluster/1',
        json={
            'description': 'test change',
        },
    )

    db_session_mock.commit.assert_not_called()

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


@pytest.mark.parametrize(
    'is_shared', [pytest.param(False, id='personal'), pytest.param(True, id='shared')],
)
@pytest.mark.parametrize(
    'is_admin', [pytest.param(False, id='user'), pytest.param(True, id='admin')],
)
def test_delete_cluster(client, db_session_mock, mocker,
                        region, project, shared_project, product, tower_client,
                        is_shared, is_admin):
    if is_shared:
        project = shared_project

    mocker.patch('rhub.api.lab.cluster._user_can_access_cluster').side_effect = (
        lambda cluster, user_id: is_admin or cluster.owner_id == user_id
    )

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

    tower_client.template_get.return_value = {'id': 123, 'name': 'dummy-delete'}
    tower_client.template_launch.return_value = {'id': 321}

    rv = client.delete(
        f'{API_BASE}/lab/cluster/1',
        headers=AUTH_HEADER,
    )

    if is_shared and not is_admin:
        assert rv.status_code == 403
        region.tower.create_tower_client.assert_not_called()
        db_session_mock.commit.assert_not_called()

    else:
        assert rv.status_code == 204
        region.tower.create_tower_client.assert_called()
        tower_client.template_get.assert_called_with(template_name='dummy-delete')
        tower_client.template_launch.assert_called_with(123, {
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
                'rhub_user_name': project.owner.name,
            },
        })

        # Clusters should not be deleted immediately
        db_session_mock.delete.assert_not_called()
        db_session_mock.commit.assert_called()


def test_delete_cluster_forbidden(client, db_session_mock, mocker):
    cluster_id = 1

    mocker.patch(
        'rhub.api.lab.cluster._user_can_access_cluster',
    ).return_value = False

    rv = client.delete(
        f'{API_BASE}/lab/cluster/{cluster_id}',
        headers=AUTH_HEADER,
    )

    model.Cluster.query.get.assert_called_with(cluster_id)

    db_session_mock.delete.assert_not_called()

    assert rv.status_code == 403, rv.data
    assert rv.json['title'] == 'Forbidden'
    assert rv.json['detail'] == "You don't have access to this cluster."


def test_delete_cluster_non_existent(client, db_session_mock):
    cluster_id = 1

    model.Cluster.query.get.return_value = None

    rv = client.delete(
        f'{API_BASE}/lab/cluster/{cluster_id}',
        headers=AUTH_HEADER,
    )

    db_session_mock.delete.assert_not_called()

    assert rv.status_code == 404, rv.data
    assert rv.json['title'] == 'Not Found'
    assert rv.json['detail'] == f'Cluster {cluster_id} does not exist'


def test_delete_cluster_unauthorized(client, db_session_mock):
    rv = client.delete(
        f'{API_BASE}/lab/cluster/1',
    )

    db_session_mock.delete.assert_not_called()

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_get_cluster_events(client, mocker, project, auth_user):
    events = [
        model.ClusterTowerJobEvent(
            id=1,
            date=datetime.datetime(2021, 1, 1, 1, 0, 0, tzinfo=tzutc()),
            user_id=auth_user.id,
            user=auth_user,
            cluster_id=1,
            tower_id=1,
            tower=tower_model.Server(id=1),
            tower_job_id=1,
            status=model.ClusterStatus.POST_PROVISIONING,
        ),
        model.ClusterReservationChangeEvent(
            id=2,
            date=datetime.datetime(2021, 1, 1, 2, 0, 0, tzinfo=tzutc()),
            user_id=auth_user.id,
            user=auth_user,
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
        headers=AUTH_HEADER,
    )

    assert rv.status_code == 200

    model.Cluster.query.get.assert_called_with(1)

    assert rv.json == [
        {
            'id': 1,
            'type': model.ClusterEventType.TOWER_JOB.value,
            'cluster_id': 1,
            'date': '2021-01-01T01:00:00+00:00',
            'user_id': auth_user.id,
            'user_name': auth_user.name,
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
            'user_id': auth_user.id,
            'user_name': auth_user.name,
            'old_value': None,
            'new_value': '2021-02-01T00:00:00+00:00',
            '_href': ANY,
        },
    ]


def test_get_cluster_events_forbidden(client, mocker):
    cluster_id = 1

    mocker.patch(
        'rhub.api.lab.cluster._user_can_access_cluster',
    ).return_value = False

    rv = client.get(
        f'{API_BASE}/lab/cluster/{cluster_id}/events',
        headers=AUTH_HEADER,
    )

    model.Cluster.query.get.assert_called_with(cluster_id)

    assert rv.status_code == 403, rv.data
    assert rv.json['title'] == 'Forbidden'
    assert rv.json['detail'] == "You don't have access to this cluster."


def test_get_cluster_events_non_existent_cluster(client):
    cluster_id = 1

    model.Cluster.query.get.return_value = None

    rv = client.get(
        f'{API_BASE}/lab/cluster/1/events',
        headers=AUTH_HEADER,
    )

    model.Cluster.query.get.assert_called_with(cluster_id)

    assert rv.status_code == 404, rv.data
    assert rv.json['title'] == 'Not Found'
    assert rv.json['detail'] == f'Cluster {cluster_id} does not exist'


def test_get_cluster_events_unauthorized(client):
    rv = client.get(
        f'{API_BASE}/lab/cluster/1/events',
    )

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


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
        headers=AUTH_HEADER,
    )

    assert rv.data == b'Ansible output.'


def test_get_cluster_event_stdout_forbidden(client, mocker):
    event_id = 1

    mocker.patch(
        'rhub.api.lab.cluster._user_can_access_cluster'
    ).return_value = False

    rv = client.get(
        f'{API_BASE}/lab/cluster_event/{event_id}/stdout',
        headers=AUTH_HEADER,
    )

    model.ClusterTowerJobEvent.query.get.assert_called_with(event_id)

    assert rv.status_code == 403, rv.data
    assert rv.json['title'] == 'Forbidden'
    assert rv.json['detail'] == "You don't have access to related cluster."


def test_get_cluster_event_stdout_non_existent(client):
    event_id = 1

    model.ClusterTowerJobEvent.query.get.return_value = None

    rv = client.get(
        f'{API_BASE}/lab/cluster_event/{event_id}/stdout',
        headers=AUTH_HEADER,
    )

    model.ClusterTowerJobEvent.query.get.assert_called_with(event_id)

    assert rv.status_code == 404, rv.data
    assert rv.json['title'] == 'Not Found'
    assert rv.json['detail'] == f'Event {event_id} does not exist'


def test_get_cluster_event_stdout_unauthorized(client):
    rv = client.get(
        f'{API_BASE}/lab/cluster_event/1/stdout',
    )

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_get_cluster_event_stdout_towererror(client, mocker):
    event = model.ClusterTowerJobEvent(
        id=1,
        date=datetime.datetime(2000, 1, 1, 1, 0, 0, tzinfo=tzutc()),
        user_id=1,
        cluster_id=1,
        tower_id=1,
        tower=tower_model.Server(id=1),
        tower_job_id=1,
        status=model.ClusterStatus.ACTIVE,
    )
    mocker.patch.object(event, 'get_tower_job_output').side_effect = TowerError

    model.ClusterTowerJobEvent.query.get.return_value = event

    rv = client.get(
        f'{API_BASE}/lab/cluster_event/1/stdout',
        headers=AUTH_HEADER,
    )

    assert rv.status_code != 200


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
        headers=AUTH_HEADER,
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


def test_get_cluster_hosts_forbidden(client, mocker):
    cluster_id = 1

    mocker.patch(
        'rhub.api.lab.cluster._user_can_access_cluster'
    ).return_value = False

    rv = client.get(
        f'{API_BASE}/lab/cluster/{cluster_id}/hosts',
        headers=AUTH_HEADER,
    )

    model.Cluster.query.get.assert_called_with(cluster_id)

    assert rv.status_code == 403, rv.data
    assert rv.json['title'] == 'Forbidden'
    assert rv.json['detail'] == "You don't have access to this cluster."


def test_get_cluster_hosts_non_existent(client):
    cluster_id = 1

    model.Cluster.query.get.return_value = None

    rv = client.get(
        f'{API_BASE}/lab/cluster/{cluster_id}/hosts',
        headers=AUTH_HEADER,
    )

    model.Cluster.query.get.assert_called_with(cluster_id)

    assert rv.status_code == 404, rv.data
    assert rv.json['title'] == 'Not Found'
    assert rv.json['detail'] == f'Cluster {cluster_id} does not exist'


def test_get_cluster_hosts_unauthorized(client):
    rv = client.get(
        f'{API_BASE}/lab/cluster/1/hosts',
    )

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


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
        headers=AUTH_HEADER,
        json=hosts_data,
    )

    assert rv.status_code == 200

    db_session_mock.add.assert_called()
    db_session_mock.commit.assert_called()

    hosts = [i.args[0] for i in db_session_mock.add.call_args_list]
    for host_data, host_row in zip(hosts_data, hosts):
        for k, v in host_data.items():
            assert getattr(host_row, k) == v


def test_create_cluster_hosts_non_existent_cluster(client, db_session_mock):
    cluster_id = 1

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

    model.Cluster.query.get.return_value = None

    rv = client.post(
        f'{API_BASE}/lab/cluster/{cluster_id}/hosts',
        headers=AUTH_HEADER,
        json=hosts_data,
    )

    model.Cluster.query.get.assert_called_with(cluster_id)

    db_session_mock.add.assert_not_called()

    assert rv.status_code == 404, rv.data
    assert rv.json['title'] == 'Not Found'
    assert rv.json['detail'] == f'Cluster {cluster_id} does not exist'


def test_create_cluster_hosts_unauthorized(client, db_session_mock):
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
        json=hosts_data,
    )

    db_session_mock.add.assert_not_called()

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


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
        headers=AUTH_HEADER,
    )

    assert rv.status_code == 204

    for host in hosts:
        db_session_mock.delete.assert_any_call(host)
    db_session_mock.commit.assert_called()


def test_delete_cluster_hosts_non_existent_cluster(client, db_session_mock):
    cluster_id = 1

    model.Cluster.query.get.return_value = None

    rv = client.delete(
        f'{API_BASE}/lab/cluster/{cluster_id}/hosts',
        headers=AUTH_HEADER,
    )

    db_session_mock.delete.assert_not_called()

    assert rv.status_code == 404, rv.data
    assert rv.json['title'] == 'Not Found'
    assert rv.json['detail'] == f'Cluster {cluster_id} does not exist'


def test_delete_cluster_hosts_unauthorized(client, db_session_mock):
    rv = client.delete(
        f'{API_BASE}/lab/cluster/1/hosts',
    )

    db_session_mock.delete.assert_not_called()

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_tower_webhook_cluster(
    client, mocker, messaging_mock, auth_user, region, project, product, tower_client,
    di_mock
):
    mocker.patch('rhub.api.tower.di', new=di_mock)

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

    tower_job_id = 53341
    payload = {
        'id': tower_job_id,
        'name': product.tower_template_name_delete,
        'url': 'https://tower.example.com/#/jobs/playbook/53341',
        'created_by': 'rhub-tower',
        'started': '2022-08-08T14:00:09.850133+00:00',
        'finished': '2022-08-08T14:02:44.576137+00:00',
        'status': 'successful',
        'traceback': '',
        'inventory': 'localhost',
        'project': 'example',
        'playbook': 'products/rhub-example-delete.yml',
        'credential': 'example',
        'limit': '',
        'extra_vars': f"""
            {{
              "rhub_cluster_id": {cluster.id},
              "rhub_cluster_name": "{cluster.name}",
              "rhub_product_id": {product.id},
              "rhub_product_name": "{product.name}",
              "rhub_region_id": {region.id},
              "rhub_region_name": "{region.name}",
              "rhub_project_id": {project.id},
              "rhub_project_name": "{project.name}",
              "rhub_user_id": {auth_user.id},
              "rhub_user_name": "{auth_user.name}"
            }}
        """,
        'hosts': {
            'localhost': {
                'failed': False,
                'changed': 3,
                'dark': 0,
                'failures': 0,
                'ok': 11,
                'processed': 1,
                'skipped': 0,
                'rescued': 0,
                'ignored': 0,
            },
        },
    }

    tower_client.template_get.return_value = {'id': 123, 'name': 'rhub-example-delete'}
    tower_client.template_launch.return_value = {'id': 321}

    rv = client.post(
        f'{API_BASE}/tower/webhook_notification',
        headers=AUTH_HEADER | {
            'Content-Type': 'application/json',
        },
        json=payload,
    )

    assert rv.status_code == 204, rv.data

    messaging_mock.send.assert_called()

    m_topic, m_msg = messaging_mock.send.call_args.args
    m_extra = messaging_mock.send.call_args.kwargs['extra']

    assert m_topic == 'lab.cluster.delete'
    assert m_extra['cluster_id'] == cluster.id
    assert m_extra['job_id'] == tower_job_id
    assert m_extra['job_status'] == 'successful'
