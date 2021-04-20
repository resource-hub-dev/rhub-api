import os
import logging

import connexion
from flask_cors import CORS
from flask import g, current_app

import rhub
from rhub.auth.keycloak import KeycloakClient


logger = logging.getLogger(__name__)


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


def create_app():
    """Create Connexion/Flask application."""
    root = os.path.dirname(rhub.__path__[0])

    connexion_app = connexion.App(
        __name__,
        specification_dir=os.path.join(root, 'openapi'),
    )
    connexion_app.add_api('openapi.yml')

    flask_app = connexion_app.app
    # Enable CORS (Cross-Origin Resource Sharing)
    # https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS
    CORS(flask_app)

    flask_app.config['LOG_LEVEL'] = os.getenv('LOG_LEVEL', 'info').upper()

    flask_app.config['KEYCLOAK_SERVER'] = os.getenv('KEYCLOAK_SERVER')
    flask_app.config['KEYCLOAK_RESOURCE'] = os.getenv('KEYCLOAK_RESOURCE')
    flask_app.config['KEYCLOAK_REALM'] = os.getenv('KEYCLOAK_REALM')
    flask_app.config['KEYCLOAK_SECRET'] = os.getenv('KEYCLOAK_SECRET')
    flask_app.config['KEYCLOAK_ADMIN_USER'] = os.getenv('KEYCLOAK_ADMIN_USER')
    flask_app.config['KEYCLOAK_ADMIN_PASS'] = os.getenv('KEYCLOAK_ADMIN_PASS')

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

    return connexion_app
