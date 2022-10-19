import datetime

import pytest
from dateutil.tz import tzutc

from rhub.lab import model, utils


@pytest.fixture
def product():
    yield model.Product(
        id=1,
        name='dummy',
        description='dummy',
        enabled=True,
        tower_template_name_create='dummy-create',
        tower_template_name_delete='dummy-delete',
        parameters={},
        flavors={},
    )


@pytest.fixture
def cluster(product):
    yield model.Cluster(
        id=1,
        name='testcluster',
        description='test cluster',
        created=datetime.datetime(2021, 1, 1, 1, 0, 0, tzinfo=tzutc()),
        region_id=1,
        region=None,
        project_id=1,
        project=None,
        reservation_expiration=None,
        lifespan_expiration=None,
        status=model.ClusterStatus.ACTIVE,
        product_id=1,
        product_params={},
        product=product,
    )


@pytest.mark.parametrize(
    'product_flavors, cluster_params, cluster_usage',
    [
        pytest.param(
            # product_flavors =
            {
                'flavor.large': {
                    'num_vcpus': 4,
                    'num_volumes': 1,
                    'ram_mb': 8192,
                    'volumes_gb': 60,
                },
            },
            # cluster_params =
            {
                'num_nodes': 2,
                'node_flavor': 'flavor.large',
            },
            # cluster_usage =
            {
                'num_vcpus': 4 * 2,
                'num_volumes': 2,
                'ram_mb': 8192 * 2,
                'volumes_gb': 60 * 2,
            },
            id='generic',
        ),
        pytest.param(
            # product_flavors =
            {
                'rgw_nodes': {
                    'num_vcpus': 2,
                    'num_volumes': 1,
                    'ram_mb': 4096,
                    'volumes_gb': 40,
                },
                'osd_nodes': {
                    'num_vcpus': 2,
                    'num_volumes': 1,
                    'ram_mb': 2048,
                    'volumes_gb': 30,
                },
            },
            # cluster_params =
            {
                'num_rgw_nodes': 1,
                'num_osd_nodes': 1,
            },
            # cluster_usage =
            {
                'num_vcpus': 2 + 2,
                'num_volumes': 1 + 1,
                'ram_mb': 4096 + 2048,
                'volumes_gb': 40 + 30,
            },
            id='common'
        ),
        pytest.param(
            # product_flavors =
            {
                'single_master_nodes': {
                    'num_vcpus': 8,
                    'num_volumes': 1,
                    'ram_mb': 16384,
                    'volumes_gb': 80,
                },
                'multi_master_nodes': {
                    'num_vcpus': 4,
                    'num_volumes': 1,
                    'ram_mb': 16384,
                    'volumes_gb': 30,
                },
            },
            # cluster_params =
            {
                'num_master_nodes': 1,
            },
            # cluster_usage =
            {
                'num_vcpus': 8,
                'num_volumes': 1,
                'ram_mb': 16384,
                'volumes_gb': 80,
            },
            id='multi_single/1',
        ),
        pytest.param(
            # product_flavors =
            {
                'single_master_nodes': {
                    'num_vcpus': 8,
                    'num_volumes': 1,
                    'ram_mb': 16384,
                    'volumes_gb': 80,
                },
                'multi_master_nodes': {
                    'num_vcpus': 4,
                    'num_volumes': 1,
                    'ram_mb': 16384,
                    'volumes_gb': 30,
                },
            },
            # cluster_params =
            {
                'num_master_nodes': 2,
            },
            # cluster_usage =
            {
                'num_vcpus': 4 * 2,
                'num_volumes': 2,
                'ram_mb': 16384 * 2,
                'volumes_gb': 30 * 2,
            },
            id='multi_single/2',
        ),
    ]
)
def test_calculate_cluster_usage(cluster, product_flavors, cluster_params, cluster_usage):
    cluster.product.flavors = product_flavors
    cluster.product_params = cluster_params

    calculated_usage = utils.calculate_cluster_usage(cluster)

    assert calculated_usage == cluster_usage
