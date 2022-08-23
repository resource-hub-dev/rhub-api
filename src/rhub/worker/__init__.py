import logging
import logging.config

from celery.signals import celeryd_init, setup_logging

from .flask_celery import FlaskCelery


celery = FlaskCelery()


@celeryd_init.connect
def init_celery_app(*args, **kwargs):
    from rhub.api import create_app

    app = create_app({'SCHEDULER_DISABLE': True})
    app.app_context().push()


@setup_logging.connect
def configure_logging(*args, **kwags):
    from rhub.api import _config

    if _config.LOGGING_CONFIG and False:
        logging.config.dictConfig(_config.LOGGING_CONFIG)
    else:
        try:
            import coloredlogs
            coloredlogs.install(level=_config.LOGGING_LEVEL)
        except ImportError:
            logging.basicConfig(level=_config.LOGGING_LEVEL)
