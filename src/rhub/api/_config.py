import os
import urllib.parse
from datetime import timedelta

KEYCLOAK_SERVER = os.getenv('KEYCLOAK_SERVER')
KEYCLOAK_RESOURCE = os.getenv('KEYCLOAK_RESOURCE')
KEYCLOAK_REALM = os.getenv('KEYCLOAK_REALM')
KEYCLOAK_SECRET = os.getenv('KEYCLOAK_SECRET')
KEYCLOAK_ADMIN_USER = os.getenv('KEYCLOAK_ADMIN_USER')
KEYCLOAK_ADMIN_PASS = os.getenv('KEYCLOAK_ADMIN_PASS')

WEBHOOK_VAULT_PATH = os.getenv('WEBHOOK_VAULT_PATH')

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

CELERY_BROKER_URL = '{type}://{username}:{password}@{host}:{port}'.format(
    type=os.getenv('RHUB_BROKER_TYPE', ''),
    host=os.getenv('RHUB_BROKER_HOST', ''),
    port=os.getenv('RHUB_BROKER_PORT', ''),
    username=os.getenv('RHUB_BROKER_USERNAME', ''),
    password=urllib.parse.quote_plus(os.getenv('RHUB_BROKER_PASSWORD', '')),
)

CELERY_RESULT_BACKEND = 'db+postgresql:' + SQLALCHEMY_DATABASE_URI.split(':', 1)[1]
CELERY_RESULT_EXPIRES = timedelta(days=7)
