import logging

import flask_migrate

from rhub.api import db
from rhub.auth import ADMIN_GROUP
from rhub.auth import model as auth_model  # noqa: F401
from rhub.lab import CLUSTER_ADMIN_GROUP, SHAREDCLUSTER_GROUP
from rhub.lab import model as lab_model  # noqa: F401
from rhub.policies import model as policies_model  # noqa: F401
from rhub.scheduler import jobs as scheduler_jobs
from rhub.scheduler import model as scheduler_model  # noqa: F401
from rhub.tower import model as tower_model  # noqa: F401


logger = logging.getLogger(__name__)


def create_cronjob(cronjob):
    """Utility to create a cron job, if it doesn't already exist."""
    query = scheduler_model.SchedulerCronJob.query.filter(
        scheduler_model.SchedulerCronJob.job_name == cronjob.job_name
    )
    if query.count() < 1:
        logger.info(f'Creating cron job {cronjob!r}.')
        db.session.add(cronjob)
        db.session.commit()


# This function must be idempotent. In container, it may be called on every
# start.
def setup():
    flask_migrate.upgrade()

    create_cronjob(
        scheduler_model.SchedulerCronJob(
            name='Delete expired clusters',
            description=(
                'Deletes clusters with expired `reservation_expiration` '
                'or `lifespan_expiration` in all regions.'
            ),
            enabled=True,
            time_expr='0 1 * * *',  # daily, 1 AM
            job_name=scheduler_jobs.delete_expired_clusters.name,
            job_params={
                'reservation_grace_period': 3,
            },
        )
    )
    create_cronjob(
        scheduler_model.SchedulerCronJob(
            name='Cleanup deleted clusters',
            description='Cleanup clusters that were successfully destroyed.',
            enabled=True,
            time_expr='0 * * * *',  # hourly
            job_name=scheduler_jobs.cleanup_deleted_clusters.name,
            job_params=None,
        )
    )

    # Initial set of locations
    locations = [
        {'name': 'AMS', 'description': 'Amsterdam'},
        {'name': 'PEK', 'description': 'Beijing'},
        {'name': 'BNE', 'description': 'Brisbane'},
        {'name': 'BRQ', 'description': 'Brno'},
        {'name': 'FAB', 'description': 'Farnborough'},
        {'name': 'PHX', 'description': 'Phoenix'},
        {'name': 'PNQ', 'description': 'Pune'},
        {'name': 'RDU', 'description': 'Raleigh'},
        {'name': 'GRU', 'description': 'São Paulo'},
        {'name': 'SIN', 'description': 'Singapore'},
        {'name': 'TLV', 'description': 'Tel Aviv'},
        {'name': 'NRT', 'description': 'Tokyo'},
    ]
    if lab_model.Location.query.count() == 0:
        for loc in locations:
            db.session.add(lab_model.Location(**loc))
        db.session.commit()

    groups = [ADMIN_GROUP, SHAREDCLUSTER_GROUP, CLUSTER_ADMIN_GROUP]
    if auth_model.Group.query.count() == 0:
        for group_name in groups:
            db.session.add(auth_model.Group(name=group_name))
        db.session.commit()
