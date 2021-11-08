import os
import logging

import connexion
import click
import prance
import injector
from flask.cli import with_appcontext
from flask_cors import CORS
from flask_injector import FlaskInjector
from flask_sqlalchemy import SQLAlchemy

import rhub
from rhub.api.vault import Vault, VaultModule
from rhub.auth.keycloak import KeycloakModule
from rhub.scheduler import SchedulerModule


logger = logging.getLogger(__name__)


di = injector.Injector()
db = SQLAlchemy()


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
    root = os.path.dirname(rhub.__path__[0])

    connexion_app = connexion.App(__name__)

    flask_app = connexion_app.app
    flask_app.url_map.strict_slashes = False

    from . import _config
    flask_app.config.from_object(_config)

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

    db.init_app(flask_app)

    try:
        import coloredlogs
        coloredlogs.install(level=flask_app.config['LOG_LEVEL'])
    except ImportError:
        logging.basicConfig(level=flask_app.config['LOG_LEVEL'])

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
            webhookCreds = di.get(Vault).read(flask_app.config['WEBHOOK_VAULT_PATH'])
            if webhookCreds:
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

    return flask_app
