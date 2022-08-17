#!/usr/bin/env python3

import logging
import os
import pathlib

from gunicorn import glogging
from ruamel import yaml


class HealthCheckFilter(logging.Filter):
    def filter(self, record):
        # Filter out healthcheck requests.
        url = record.args['U']
        return not url.endswith('/ping') and not url.endswith('/cowsay')


class CustomGunicornLogger(glogging.Logger):
    def setup(self, cfg):
        super().setup(cfg)
        self.access_log.addFilter(HealthCheckFilter())


LOG_LEVEL = os.getenv('LOG_LEVEL', 'warning')
LOG_CONFIG = os.getenv('LOG_CONFIG')

FLASK_ENV = os.getenv('FLASK_ENV', 'development')
FLASK_RUN_HOST = os.getenv('FLASK_RUN_HOST', '0.0.0.0')
FLASK_RUN_PORT = os.getenv('FLASK_RUN_PORT', 8081)

bind = f'{FLASK_RUN_HOST}:{FLASK_RUN_PORT}'
reload = FLASK_ENV == 'development'
reload_extra_files = [str(path.resolve()) for path in pathlib.Path('src/rhub/openapi/').glob('**/*.yml')]

if LOG_CONFIG and os.path.exists(LOG_CONFIG):
    with open(LOG_CONFIG, 'r') as f:
        logconfig_dict = yaml.safe_load(f)
else:
    loglevel = LOG_LEVEL

logger_class = CustomGunicornLogger

# Must be set to True, otherwise scheduler and messaging thread are started
# multiple times in each of gunicorn worker.
preload_app = True


from prometheus_flask_exporter.multiprocess import GunicornInternalPrometheusMetrics


def child_exit(server, worker):
    GunicornInternalPrometheusMetrics.mark_process_dead_on_child_exit(worker.pid)
