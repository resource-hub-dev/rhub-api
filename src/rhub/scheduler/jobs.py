import logging

import rhub.tower.model
import rhub.lab.model
from rhub.api import db
from rhub.api.utils import date_now


logger = logging.getLogger(__name__)


class CronJob:
    __jobs = {}

    def __init__(self, fn):
        self.fn = fn
        self.__class__.__jobs[self.name] = self

    def __repr__(self):
        return f'<CronJob {self.fn.__name__}>'

    @property
    def name(self):
        return self.fn.__name__

    @property
    def doc(self):
        return self.fn.__doc__

    def __call__(self, *args, **kwargs):
        return self.fn(*args, **kwargs)

    @classmethod
    def get_jobs(cls):
        """
        Get all cron jobs, dict with job name as a key and :class:`CronJob`
        instance as a value.
        """
        return cls.__jobs


@CronJob
def example(params):
    """Example cron job."""
    logger.info(f'Executing example cron job, {params=}')


@CronJob
def tower_launch(params):
    """
    Launch template in Tower.

    params:
        tower_id -- ID of the Tower server in tower module
            (:class:`rhub.tower.model.Server`)
        template_id -- ID of the template in the Tower
        template_is_workflow -- bool if the template in Tower is workflow
            template, optional, default is `False`
        extra_vars -- dict of extra variables to pass to template, optiona,
            default is empty dict
    """
    server = rhub.tower.model.Server.query.get(params['tower_id'])
    client = server.create_tower_client()

    template_id = params['template_id']
    extra_vars = params.get('extra_vars', {})

    if params.get('template_is_workflow', False):
        launch = client.workflow_launch
        template_type = 'workflow template'
    else:
        launch = client.template_launch
        template_type = 'template'

    job_data = launch(template_id, extra_vars)
    logger.info(
        f'Launched {template_type} {template_id} in Tower {server.name} '
        f'(ID: {server.id}), job ID in Tower: {job_data["id"]}'
    )


@CronJob
def delete_expired_clusters(params):
    """
    Delete expired clusters.

    params:
        None
    """
    now = date_now()

    expired_clusters = rhub.lab.model.Cluster.query.filter(
        db.or_(
            db.and_(
                ~rhub.lab.model.Cluster.reservation_expiration.is_(None),
                rhub.lab.model.Cluster.reservation_expiration <= now,
            ),
            db.and_(
                ~rhub.lab.model.Cluster.lifespan_expiration.is_(None),
                rhub.lab.model.Cluster.lifespan_expiration <= now,
            ),
        )
    )

    for cluster in expired_clusters.all():
        logger.info(
            f'Deleting expired cluster "{cluster.name}" ({cluster.id=}, '
            f'{cluster.reservation_expiration=}, {cluster.lifespan_expiration=})',
            extra={'cluster': cluster.to_dict(), 'region': cluster.region.to_dict()},
        )

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

            db.session.delete(cluster)
            db.session.commit()

        except Exception as e:
            logger.exception(e)
