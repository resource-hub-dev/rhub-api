import logging
import os
import urllib.parse
from datetime import timedelta
from pathlib import Path

import dynaconf
import yaml


config = dynaconf.Dynaconf(
    settings_files=os.environ['RHUB_CONFIG'].split(':'),
    envvar_prefix='RHUB',
)


RHUB_CONFIG_DIR = Path(os.getenv('RHUB_CONFIG_DIR', '/tmp/config'))
RHUB_DATA_DIR = Path(os.getenv('RHUB_DATA_DIR', '/tmp/data'))


AUTH_OIDC_ENDPOINT = os.getenv('AUTH_OIDC_ENDPOINT')
AUTH_OIDC_ALLOW_ISSUER_MISMATCH = (
    os.getenv('AUTH_OIDC_ALLOW_ISSUER_MISMATCH', '').lower()
    in ['true', 'yes', '1']
)
AUTH_OIDC_UUID_ATTR = os.getenv('AUTH_OIDC_UUID_ATTR')

# DB_TYPE can be 'postgresq', 'postgresql+psycopg', ... any postgres
# implementation.
db_type = os.getenv('RHUB_DB_TYPE', '')
if 'postgresql' not in db_type:
    raise Exception(f"Unsupported database: '{db_type}', only postgresql is supported")

# See https://docs.sqlalchemy.org/en/14/core/engines.html
SQLALCHEMY_DATABASE_URI = (
    '{type}://{username}:{password}@{host}:{port}/{database}'.format(
        type=os.getenv('RHUB_DB_TYPE', ''),
        host=os.getenv('RHUB_DB_HOST', ''),
        port=os.getenv('RHUB_DB_PORT', ''),
        username=os.getenv('RHUB_DB_USERNAME', ''),
        password=urllib.parse.quote_plus(os.getenv('RHUB_DB_PASSWORD', '')),
        database=os.getenv('RHUB_DB_DATABASE', '')
    )
)
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ECHO = os.getenv('SQLALCHEMY_ECHO', 'false').lower() == 'true'

VAULT_TYPE = os.getenv('VAULT_TYPE')
# hashicorp vault variables
VAULT_ADDR = os.getenv('VAULT_ADDR')
VAULT_ROLE_ID = os.getenv('VAULT_ROLE_ID')
VAULT_SECRET_ID = os.getenv('VAULT_SECRET_ID')
# file vault variables
VAULT_PATH = os.getenv('VAULT_PATH')

SCHEDULER_API_ENABLED = False

RHUB_BROKER_URL = '{type}://{username}:{password}@{host}:{port}'.format(
    type=os.getenv('RHUB_BROKER_TYPE', ''),
    host=os.getenv('RHUB_BROKER_HOST', ''),
    port=os.getenv('RHUB_BROKER_PORT', ''),
    username=os.getenv('RHUB_BROKER_USERNAME', ''),
    password=urllib.parse.quote_plus(os.getenv('RHUB_BROKER_PASSWORD', '')),
)
RHUB_BROKER_MESSAGING_EXCHANGE = os.getenv('RHUB_BROKER_MESSAGING_EXCHANGE', '')

CELERY_BROKER_URL = RHUB_BROKER_URL
CELERY_RESULT_BACKEND = 'db+postgresql:' + SQLALCHEMY_DATABASE_URI.split(':', 1)[1]
CELERY_RESULT_EXPIRES = timedelta(days=7)

# required on celery worker to generate external urls
# https://flask.palletsprojects.com/en/2.1.x/config/#SERVER_NAME
SERVER_NAME = os.getenv('FLASK_SERVER_NAME')


_log_config_path = os.getenv('LOG_CONFIG')
if _log_config_path and os.path.exists(_log_config_path):
    try:
        with open(_log_config_path, 'r') as f:
            LOGGING_CONFIG = yaml.safe_load(f)
    except Exception:
        logging.exception(
            f'Failed to load logging configuration from {_log_config_path!r}!'
        )
        LOGGING_CONFIG = None
else:
    LOGGING_CONFIG = None

LOGGING_LEVEL = os.getenv('LOG_LEVEL', 'info')

SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = int(os.environ['SMTP_PORT']) if os.getenv('SMTP_PORT') else 25
EMAIL_FROM = os.getenv('EMAIL_FROM')
EMAIL_REPLY_TO = os.getenv('EMAIL_REPLY_TO')
EMAIL_FOOTER_LINKS = config.get('messaging.email.footer_links', default=[])

LDAP = config.ldap
