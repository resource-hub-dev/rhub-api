import logging
import logging.config
import os

import click
import connexion
import flask
import injector
import prance
from flask.cli import with_appcontext
from flask_cors import CORS
from flask_injector import FlaskInjector
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from jinja2 import BaseLoader, Environment
from prometheus_flask_exporter.multiprocess import GunicornInternalPrometheusMetrics
from ruamel import yaml

from rhub import ROOT_PKG_PATH
from rhub.api.extensions import celery
from rhub.api.vault import Vault, VaultModule
from rhub.auth.keycloak import KeycloakModule
from rhub.scheduler import SchedulerModule


logger = logging.getLogger(__name__)

di = injector.Injector()
db = SQLAlchemy()
migrate = Migrate()
jinja_env = Environment(loader=BaseLoader())

DEFAULT_PAGE_LIMIT = 20


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
    log_config = os.getenv('LOG_CONFIG')
    if log_config and os.path.exists(log_config):
        with open(log_config, 'r') as f:
            logging.config.dictConfig(yaml.safe_load(f))
    else:
        log_level = os.getenv('LOG_LEVEL', 'info').upper()
        try:
            import coloredlogs
            coloredlogs.install(level=log_level)
        except ImportError:
            logger.addHandler(flask.logging.default_handler)
            logger.setLevel(log_level)

    connexion_app = connexion.App(__name__)

    flask_app = connexion_app.app
    flask_app.url_map.strict_slashes = False
    if os.getenv('PROMETHEUS_MULTIPROC_DIR'):
        GunicornInternalPrometheusMetrics(flask_app)

    from . import _config
    flask_app.config.from_object(_config)

    parser = prance.ResolvingParser(str(ROOT_PKG_PATH / 'openapi' / 'openapi.yml'))
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

    db.init_app(flask_app)
    migrate.init_app(flask_app, db)
    celery.init_app(flask_app)

    RHUB_RETURN_INITIAL_FLASK_APP = os.getenv('RHUB_RETURN_INITIAL_FLASK_APP', 'False')
    if str(RHUB_RETURN_INITIAL_FLASK_APP).lower() == 'true':
        return flask_app

    FlaskInjector(
        app=flask_app,
        injector=di,
        modules=[
            KeycloakModule(flask_app),
            VaultModule(flask_app),
            SchedulerModule(flask_app),
        ],
    )

    # Try to retrieve Tower notification webhook creds from vault
    try:
        with flask_app.app_context():
            vault = di.get(Vault)
            webhookCreds = vault.read(flask_app.config['WEBHOOK_VAULT_PATH'])
            if webhookCreds:
                flask_app.config['WEBHOOK_USER'] = webhookCreds['username']
                flask_app.config['WEBHOOK_PASS'] = webhookCreds['password']
            else:
                raise Exception(
                    'Missing tower webhook notification credentials; '
                    f'{vault} {flask_app.config["WEBHOOK_VAULT_PATH"]}'
                )

    except Exception as e:
        logger.error(
            f'Failed to load {flask_app.config["WEBHOOK_VAULT_PATH"]} tower'
            f' webhook notification credentials {e!s}.'
        )

    return flask_app
