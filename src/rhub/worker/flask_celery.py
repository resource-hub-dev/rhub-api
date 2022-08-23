# based on https://stackoverflow.com/a/14146403

import flask
from celery import Celery
from kombu import Queue


class FlaskCelery(Celery):
    def __init__(self, *args, **kwargs):
        super(FlaskCelery, self).__init__(*args, **kwargs)
        self.app = None
        self.patch_task()

        if 'app' in kwargs:
            self.init_app(kwargs['app'])

    def patch_task(self):
        TaskBase = self.Task
        _celery = self

        class ContextTask(TaskBase):
            abstract = True

            def __call__(self, *args, **kwargs):
                if flask.has_app_context():
                    return TaskBase.__call__(self, *args, **kwargs)
                else:
                    with _celery.app.app_context():
                        return TaskBase.__call__(self, *args, **kwargs)

        self.Task = ContextTask

    def init_app(self, app):
        self.app = app

        self.config_from_object(app.config)

        self.conf.broker_url = app.config['CELERY_BROKER_URL']
        self.conf.result_backend = app.config['CELERY_RESULT_BACKEND']

        self.conf.task_default_queue = 'celery.default'
        self.conf.task_queues = (
            Queue('celery.default', queue_arguments={'x-max-priority': 10}),
        )
        self.conf.task_queue_max_priority = 10
        self.conf.task_default_priority = 5

        # Default is 4, but then queue can't prioritize messages (tasks),
        # because they get downloaded to workers before sorting happens.
        self.conf.worker_prefetch_multiplier = 1
