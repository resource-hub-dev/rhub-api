import os
import logging

import connexion
from flask_cors import CORS
from flask import g

import rhub
from rhub.api import config
from rhub.auth.keycloak import KeycloakClient


logger = logging.getLogger(__name__)


# Note: this works only when 'rhub' is namespace
ROOT = os.path.dirname(rhub.__path__[0])

app = connexion.FlaskApp(__name__, specification_dir=os.path.join(ROOT, 'openapi'))
app.add_api('openapi.yml')

CORS(app.app)


@app.app.before_request
def before_request():
    if config.KEYCLOAK_SERVER:
        g.keycloak = KeycloakClient(
            server=config.KEYCLOAK_SERVER,
            resource=config.KEYCLOAK_RESOURCE,
            realm=config.KEYCLOAK_REALM,
            secret=config.KEYCLOAK_SECRET,
            admin_user=config.KEYCLOAK_ADMIN_USER,
            admin_pass=config.KEYCLOAK_ADMIN_PASS,
        )
    else:
        logger.warning(
            '"g.keycloak" (KeycloakClient) not initialized due to missing '
            'configuration, auth endpoints will not work.'
        )
