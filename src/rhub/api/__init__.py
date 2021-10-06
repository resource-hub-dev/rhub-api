import os
import logging
import urllib.parse

import connexion
import click
import prance
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_apscheduler import APScheduler
from flask import g, current_app
from flask.cli import with_appcontext

import rhub
from rhub.auth.keycloak import KeycloakClient
from rhub.api.vault import Vault, HashicorpVault, FileVault


logger = logging.getLogger(__name__)


db = SQLAlchemy()
sched = APScheduler()


DEFAULT_PAGE_LIMIT = 20


def get_keycloak() -> KeycloakClient:
    """Get KeycloakClient instance."""
    if 'keycloak' not in g:
        g.keycloak = KeycloakClient(
            server=current_app.config['KEYCLOAK_SERVER'],
            resource=current_app.config['KEYCLOAK_RESOURCE'],
            realm=current_app.config['KEYCLOAK_REALM'],
            secret=current_app.config['KEYCLOAK_SECRET'],
            admin_user=current_app.config['KEYCLOAK_ADMIN_USER'],
            admin_pass=current_app.config['KEYCLOAK_ADMIN_PASS'],
        )
    return g.keycloak


def get_vault() -> Vault:
    if 'vault' not in g:
        vault_type = current_app.config['VAULT_TYPE']
        if vault_type == 'hashicorp':
            g.vault = HashicorpVault(
                url=current_app.config['VAULT_ADDR'],
                role_id=current_app.config['VAULT_ROLE_ID'],
                secret_id=current_app.config['VAULT_SECRET_ID'],
            )
        elif vault_type == 'file':
            g.vault = FileVault(
                current_app.config['VAULT_PATH'],
            )
        else:
            logger.error(f'Unknown vault type {vault_type}')
            raise Exception(f'Unknown vault type {vault_type}')
    return g.vault


def init_app():
    logger.info('Starting initialization...')
    from ._setup import setup
    setup()
    logger.info('Initialization finished.')


@click.command('init')
@with_appcontext
def init_command():
    init_app()


def create_app():
    """Create Connexion/Flask application."""
    root = os.path.dirname(rhub.__path__[0])

    connexion_app = connexion.App(__name__)

    flask_app = connexion_app.app
    flask_app.url_map.strict_slashes = False

    parser = prance.ResolvingParser(os.path.join(root, 'openapi', 'openapi.yml'))
    connexion_app.add_api(
        parser.specification,
        validate_responses=True,
        strict_validation=True,
        pythonic_params=True,
    )

    # Enable CORS (Cross-Origin Resource Sharing)
    # https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS
    CORS(flask_app)

    flask_app.cli.add_command(init_command)

    flask_app.config['LOG_LEVEL'] = os.getenv('LOG_LEVEL', 'info').upper()

    flask_app.config['KEYCLOAK_SERVER'] = os.getenv('KEYCLOAK_SERVER')
    flask_app.config['KEYCLOAK_RESOURCE'] = os.getenv('KEYCLOAK_RESOURCE')
    flask_app.config['KEYCLOAK_REALM'] = os.getenv('KEYCLOAK_REALM')
    flask_app.config['KEYCLOAK_SECRET'] = os.getenv('KEYCLOAK_SECRET')
    flask_app.config['KEYCLOAK_ADMIN_USER'] = os.getenv('KEYCLOAK_ADMIN_USER')
    flask_app.config['KEYCLOAK_ADMIN_PASS'] = os.getenv('KEYCLOAK_ADMIN_PASS')

    flask_app.config['WEBHOOK_VAULT_PATH'] = os.getenv('WEBHOOK_VAULT_PATH')

    # DB_TYPE can be 'postgresq', 'postgresql+psycopg', ... any postgres
    # implementation.
    if 'postgresql' not in os.environ.get('DB_TYPE', ''):
        raise Exception('Unsupported database, only postgresql is supported')

    # See https://docs.sqlalchemy.org/en/14/core/engines.html
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = (
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

    db.init_app(flask_app)

    flask_app.config['VAULT_TYPE'] = os.getenv('VAULT_TYPE')
    # hashicorp vault variables
    flask_app.config['VAULT_ADDR'] = os.getenv('VAULT_ADDR')
    flask_app.config['VAULT_ROLE_ID'] = os.getenv('VAULT_ROLE_ID')
    flask_app.config['VAULT_SECRET_ID'] = os.getenv('VAULT_SECRET_ID')
    # file vault variables
    flask_app.config['VAULT_PATH'] = os.getenv('VAULT_PATH')

    try:
        import coloredlogs
        coloredlogs.install(level=flask_app.config['LOG_LEVEL'])
    except ImportError:
        logging.basicConfig(level=flask_app.config['LOG_LEVEL'])

    # Try to create keycloak client to report early if something is wrong.
    try:
        with flask_app.app_context():
            get_keycloak()
    except Exception as e:
        logger.warning(
            f'Failed to create keycloak instance {e!s}, auth endpoints will not work.'
        )

    # Try to create vault client and report errors.
    try:
        with flask_app.app_context():
            vault = get_vault()
    except Exception as e:
        logger.warning(
            f'Failed to create {flask_app.config["VAULT_TYPE"]} vault instance {e!s}.'
        )

    # Try to retrieve Tower notification webhook creds from vault
    try:
        with flask_app.app_context():
            webhookCreds = vault.read(current_app.config['WEBHOOK_VAULT_PATH'])
            if (webhookCreds):
                flask_app.config['WEBHOOK_USER'] = webhookCreds['username']
                flask_app.config['WEBHOOK_PASS'] = webhookCreds['password']
            else:
                logger.error('Missing tower webhook notification credentials')
                raise Exception('Missing tower webhook notification credentials')

    except Exception as e:
        logger.warning(
            f'Failed to load {flask_app.config["WEBHOOK_VAULT_PATH"]} tower'
            f' webhook notification credentials {e!s}.'
        )

    flask_app.config['SCHEDULER_API_ENABLED'] = False

    sched.init_app(flask_app)

    @sched.task('interval', id='rhub_scheduler', seconds=60, max_instances=1)
    def rhub_scheduler():
        from rhub import scheduler
        with flask_app.app_context():
            scheduler.run()

    sched.start()

    return flask_app
