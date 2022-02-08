#!/usr/bin/env python3

import os
import pathlib

LOG_LEVEL = os.getenv('LOG_LEVEL', 'warning')
FLASK_ENV = os.getenv('FLASK_ENV', 'development')
FLASK_RUN_HOST = os.getenv('FLASK_RUN_HOST', '0.0.0.0')
FLASK_RUN_PORT = os.getenv('FLASK_RUN_PORT', 8081)

bind = f'{FLASK_RUN_HOST}:{FLASK_RUN_PORT}'
loglevel = LOG_LEVEL
reload = FLASK_ENV == 'development'
reload_extra_files = [str(path.resolve()) for path in pathlib.Path('src/openapi/').glob('*.yml')]

# preload_app = True

from prometheus_flask_exporter.multiprocess import GunicornInternalPrometheusMetrics

def child_exit(server, worker):
    GunicornInternalPrometheusMetrics.mark_process_dead_on_child_exit(worker.pid)

