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
