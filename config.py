#!/usr/bin/env python3

import os

LOG_LEVEL = os.getenv('LOG_LEVEL', 'warning')
FLASK_ENV = os.getenv('FLASK_ENV', 'development')
FLASK_RUN_HOST = os.getenv('FLASK_RUN_HOST', '0.0.0.0')
FLASK_RUN_PORT = os.getenv('FLASK_RUN_PORT', 8081)

bind = f'{FLASK_RUN_HOST}:{FLASK_RUN_PORT}'
loglevel = LOG_LEVEL
reload = FLASK_ENV == 'development'

#preload_app = True

