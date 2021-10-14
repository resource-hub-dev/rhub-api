import os
import urllib.parse


LOG_LEVEL = os.getenv('LOG_LEVEL', 'info').upper()

KEYCLOAK_SERVER = os.getenv('KEYCLOAK_SERVER')
KEYCLOAK_RESOURCE = os.getenv('KEYCLOAK_RESOURCE')
KEYCLOAK_REALM = os.getenv('KEYCLOAK_REALM')
KEYCLOAK_SECRET = os.getenv('KEYCLOAK_SECRET')
KEYCLOAK_ADMIN_USER = os.getenv('KEYCLOAK_ADMIN_USER')
KEYCLOAK_ADMIN_PASS = os.getenv('KEYCLOAK_ADMIN_PASS')

WEBHOOK_VAULT_PATH = os.getenv('WEBHOOK_VAULT_PATH')

# DB_TYPE can be 'postgresq', 'postgresql+psycopg', ... any postgres
# implementation.
if 'postgresql' not in os.environ.get('DB_TYPE', ''):
    raise Exception('Unsupported database, only postgresql is supported')

# See https://docs.sqlalchemy.org/en/14/core/engines.html
SQLALCHEMY_DATABASE_URI = (
    '{type}://{username}:{password}@{host}:{port}/{database}'
    .format(
        type=os.environ['DB_TYPE'],
        host=os.environ['DB_HOST'],
        port=os.environ['DB_PORT'],
        username=os.environ['DB_USERNAME'],
        password=urllib.parse.quote_plus(os.environ['DB_PASSWORD']),
        database=os.environ['DB_DATABASE'],
    )
)
SQLALCHEMY_TRACK_MODIFICATIONS = False

VAULT_TYPE = os.getenv('VAULT_TYPE')
# hashicorp vault variables
VAULT_ADDR = os.getenv('VAULT_ADDR')
VAULT_ROLE_ID = os.getenv('VAULT_ROLE_ID')
VAULT_SECRET_ID = os.getenv('VAULT_SECRET_ID')
# file vault variables
VAULT_PATH = os.getenv('VAULT_PATH')

SCHEDULER_API_ENABLED = False
