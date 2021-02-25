import os

import connexion
from flask_cors import CORS

import rhub


# Note: this works only when 'rhub' is namespace
ROOT = os.path.dirname(rhub.__path__[0])

app = connexion.FlaskApp(__name__, specification_dir=os.path.join(ROOT, 'openapi'))
app.add_api('openapi.yml')

CORS(app.app)
