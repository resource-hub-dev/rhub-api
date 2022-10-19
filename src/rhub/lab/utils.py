import logging

from rhub.api import db
from rhub.api.utils import date_now
from rhub.lab import model


logger = logging.getLogger(__name__)


def delete_cluster(cluster, user=None):
    try:
        tower_client = cluster.region.tower.create_tower_client()
        tower_template = tower_client.template_get(
            template_name=cluster.product.tower_template_name_delete,
        )

        logger.info(
            f'Launching Tower template {tower_template["name"]} '
            f'(id={tower_template["id"]}), '
            f'extra_vars={cluster.tower_launch_extra_vars!r}'
        )
        tower_client.template_launch(
            tower_template['id'],
            {'extra_vars': cluster.tower_launch_extra_vars},
        )

        tower_job = {'id': 0}

        cluster_event = model.ClusterTowerJobEvent(
            cluster_id=cluster.id,
            user_id=user,
            date=date_now(),
            tower_id=cluster.region.tower_id,
            tower_job_id=tower_job['id'],
            status=model.ClusterStatus.DELETION_QUEUED,
        )
        db.session.add(cluster_event)

        cluster.status = model.ClusterStatus.DELETION_QUEUED

        db.session.commit()
        logger.info(f'Cluster {cluster.name} (id {cluster.id}) queued for deletion '
                    f'by user {user}')

    except Exception as e:
        db.session.rollback()
        logger.exception(
            f'Failed to trigger cluster ID={cluster.id} deletion in Tower, {e!s}'
        )
        raise


def calculate_cluster_usage(cluster):
    """
    Calculate cluster usage from cluster parameters and product flavors. Should
    only be used before creating a new cluster to check if the region quota will
    be exceeded.
    """
    product = cluster.product
    params = cluster.product_params

    node_consumption = dict.fromkeys(model.Quota.FIELDS, 0)

    for param_name in params:
        # Filter out parameters not containing node number.
        if not (param_name.startswith('num_') and param_name.endswith('_nodes')):
            continue

        num_nodes = int(params[param_name])
        node_flavor_name = param_name.removeprefix('num_')

        # Generic product has only one node type and the flavor is specified in
        # parameters.
        if node_flavor_name == 'nodes':
            node_flavor_name = params['node_flavor']

        # Some product use differend flavors depending on how many nodes
        # user wants to provision. In that case, flavor X does not exist, and
        # flavors single_X and multi_X are defined instead.
        elif node_flavor_name not in product.flavors:
            if num_nodes == 1:
                node_flavor_name = f'single_{node_flavor_name}'
            else:
                node_flavor_name = f'multi_{node_flavor_name}'

        if node_flavor_name not in product.flavors:
            raise ValueError(
                f'Undefined flavor {node_flavor_name!r} in the product '
                f'ID={product.id}. Flavor name was extracted from cluster '
                f'parameter {param_name!r}.'
            )

        node_flavor = product.flavors[node_flavor_name]
        for k in node_flavor:
            node_consumption[k] += num_nodes * node_flavor[k]

    return node_consumption
