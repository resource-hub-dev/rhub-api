from sqlalchemy.orm import validates
from cron_validator import CronValidator

from rhub.api import db
from rhub.api.utils import ModelMixin
from rhub.scheduler import jobs


class SchedulerCronJob(db.Model, ModelMixin):
    __tablename__ = 'scheduler_cron'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)
    description = db.Column(db.Text, default='', nullable=False)
    enabled = db.Column(db.Boolean, default=True)
    #: cron time expression, see man 5 crontab
    time_expr = db.Column(db.String(128), nullable=False)
    job_name = db.Column(db.Text, nullable=False)
    job_params = db.Column(db.JSON, nullable=True)
    last_run = db.Column(db.DateTime(timezone=True), nullable=True)

    @validates('time_expr')
    def validate_time_expr(self, key, value):
        if not CronValidator.parse(value):
            raise ValueError(f'Cron time expression {value!r} is not valid')
        return value

    @validates('job_name')
    def validate_job_name(self, key, value):
        if value not in jobs.CronJob.get_jobs():
            raise ValueError('CronJob is not defined')
        return value

    @property
    def job(self):
        """Get job instance :class:`jobs.CronJob`."""
        return jobs.CronJob.get_jobs()[self.job_name]
