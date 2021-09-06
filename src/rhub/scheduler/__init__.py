import logging

from cron_validator import CronValidator

from rhub.api import db
from rhub.api.utils import date_now
from rhub.scheduler import model


logger = logging.getLogger(__name__)


def run():
    now = date_now()

    sched_job_query = model.SchedulerCronJob.query.filter(
        model.SchedulerCronJob.enabled.is_(True),
    )
    for sched_job in sched_job_query:
        if not CronValidator.match_datetime(sched_job.time_expr, now):
            continue

        logger.info(f'Executing scheduled job {sched_job.id} ({sched_job.job_name})')
        try:
            sched_job.job(sched_job.job_params)
            logger.info(
                f'Scheduled job {sched_job.id} ({sched_job.job_name}) succeeded'
            )
        except Exception as e:
            logger.exception(
                f'Scheduled job {sched_job.id} ({sched_job.job_name}) failed, {e!s}'
            )

        sched_job.last_run = now
        db.session.commit()
