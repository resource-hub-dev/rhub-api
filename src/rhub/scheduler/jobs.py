import logging


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
