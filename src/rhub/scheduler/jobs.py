import contextlib
import datetime
import logging

import rhub.tower.model
from rhub.api import db, di
from rhub.api.utils import date_now
from rhub.auth import tasks as auth_tasks
from rhub.lab import model as lab_model
from rhub.lab import utils as lab_utils
from rhub.messaging import Messaging
from rhub.worker import celery


logger = logging.getLogger(__name__)


class CronJob:
    __jobs = {}

    def __init__(self, fn):
        self.fn = fn
        self.task = celery.task(fn, ignore_result=True)
        self.__class__.__jobs[self.name] = self

    def __repr__(self):
        return f'<CronJob {self.fn.__name__}>'

    @property
    def name(self):
        return self.fn.__name__

    @property
    def doc(self):
        return self.fn.__doc__

    def __call__(self, params):
        if params is None:
            params = {}
        return self.task.delay(params)

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
        reservation_grace_period -- 'grace' period for reservation expiration,
            if cluster reservation is not extended it will be deleted after N
            days. This only applies to reservation (soft limit), if lifespan
            (hard limit) expires cluster is deleted immediately.
    """
    messaging = di.get(Messaging)

    now = date_now()
    reservation_grace_period = datetime.timedelta(
        days=params.get('reservation_grace_period', 0),
    )

    expired_clusters = lab_model.Cluster.query.filter(
        db.and_(
            lab_model.Cluster.status == lab_model.ClusterStatus.ACTIVE,
            db.or_(
                db.and_(
                    ~lab_model.Cluster.reservation_expiration.is_(None),
                    lab_model.Cluster.reservation_expiration <= now,
                ),
                db.and_(
                    ~lab_model.Cluster.lifespan_expiration.is_(None),
                    lab_model.Cluster.lifespan_expiration <= now,
                ),
            ),
        )
    )

    for cluster in expired_clusters.all():
        lifespan_expired = (
            cluster.lifespan_expiration
            and cluster.lifespan_expiration <= now
        )
        reservation_expired = (
            cluster.reservation_expiration
            and cluster.reservation_expiration <= now - reservation_grace_period
        )

        delete = lifespan_expired or reservation_expired
        delete_date = cluster.reservation_expiration + reservation_grace_period

        msg_extra = {
            'owner_id': cluster.owner_id,
            'owner_name': cluster.owner.name,
            'cluster_id': cluster.id,
            'cluster_name': cluster.name,
            'cluster_reservation_expiration': (
                cluster.reservation_expiration.isoformat()
                if cluster.reservation_expiration
                else None
            ),
            'cluster_lifespan_expiration': (
                cluster.lifespan_expiration.isoformat()
                if cluster.lifespan_expiration
                else None
            ),
            'cluster_delete': delete,
            'cluster_delete_date': delete_date.isoformat(),
        }

        if delete:
            logger.info(
                f'Deleting expired cluster "{cluster.name}" ({cluster.id=}, '
                f'{cluster.reservation_expiration=}, {cluster.lifespan_expiration=})',
                extra={'cluster': cluster.to_dict(), 'region': cluster.region.to_dict()},
            )
            messaging.send(
                'lab.cluster.delete',
                f'Deleting expired cluser "{cluster.name}" (ID={cluster.id})',
                extra=msg_extra,
            )

            with contextlib.suppress(Exception):
                lab_utils.delete_cluster(cluster)

        else:
            messaging.send(
                'lab.cluster.delete',
                f'Cluster "{cluster.name}" (ID={cluster.id}) has expired and '
                f'will be deleted at {delete_date:%Y-%m-%d %H:%M %Z}.',
                extra=msg_extra,
            )


@CronJob
def cleanup_deleted_clusters(params):
    deleted_clusters = lab_model.Cluster.query.filter(
        lab_model.Cluster.status == lab_model.ClusterStatus.DELETED
    )
    for cluster in deleted_clusters:
        logger.info(
            f'Cleaning deleted cluster "{cluster.name}" ({cluster.id=})',
            extra={'cluster': cluster.to_dict(), 'region': cluster.region.to_dict()},
        )
        try:
            db.session.delete(cluster)
            db.session.commit()
        except Exception:
            logger.exception(
                f'Cleanup of deleted cluster "{cluster.name}" ({cluster.id=}) failed'
            )


@CronJob
def update_ldap_data(params):
    auth_tasks.cleanup_users()
    auth_tasks.update_users()
    auth_tasks.cleanup_groups()
    auth_tasks.update_groups()
