import json
import logging
import logging.config
import os
import urllib.parse

import click
import connexion
import flask
import injector
import prance
import psycopg2.errors
import sqlalchemy.exc
from connexion import problem
from flask.cli import with_appcontext
from flask_cors import CORS
from flask_injector import FlaskInjector
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from jinja2 import BaseLoader, Environment
from prometheus_flask_exporter.multiprocess import GunicornInternalPrometheusMetrics
from werkzeug import Response

from rhub import ROOT_PKG_PATH
from rhub.api.vault import VaultModule
from rhub.auth.ldap import LdapModule
from rhub.messaging import MessagingModule
from rhub.scheduler import SchedulerModule
from rhub.worker import celery


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


@click.command('create-user')
@click.argument('user_name')
@click.option('-g', 'group_name')
@with_appcontext
def create_user_command(user_name, group_name):
    from rhub.auth import model as auth_model

    user = auth_model.User(name=user_name)
    db.session.add(user)
    db.session.flush()

    if group_name:
        group = auth_model.Group.query.filter(
            auth_model.Group.name == group_name
        ).first()
        user_group = auth_model.UserGroup(user_id=user.id, group_id=group.id)
        db.session.add(user_group)

    token_plain, token = auth_model.Token.generate(user_id=user.id)
    db.session.add(token)

    db.session.commit()
    click.secho(
        '\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n'
        f'  User ID:    {user.id}\n'
        f'  API Token:  {token_plain}\n'
        '~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n',
        bold=True,
    )


@click.command('create-token')
@click.argument('user_name')
def create_token_command(user_name):
    from rhub.auth import model as auth_model

    user = auth_model.User.query.filter(auth_model.User.name == user_name).first()
    if not user:
        raise click.Abort

    token_plain, token = auth_model.Token.generate(user_id=user.id)
    db.session.add(token)
    db.session.commit()
    click.secho(
        '\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n'
        f'  User ID:    {user.id}\n'
        f'  API Token:  {token_plain}\n'
        '~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n',
        bold=True,
    )


def log_request():
    try:
        path = flask.request.path.rstrip('/')
        if (path == '/v0/openapi.json' or path.startswith('/v0/ui')
                or path.endswith('/ping')):
            return

        request_method = flask.request.method
        request_path = flask.request.path
        request_query = urllib.parse.unquote(flask.request.query_string.decode())
        if flask.request.content_type == 'application/json' and flask.request.data:
            request_data = flask.request.json
        else:
            request_data = flask.request.data

        logger.debug(
            f'{request_method=} {request_path=} {request_query=} {request_data=}',
        )

    except Exception:
        logger.exception('Failed to log request (DEBUG logging)')


def log_response(response):
    try:
        path = flask.request.path.rstrip('/')
        if (path == '/v0/openapi.json' or path.startswith('/v0/ui')
                or path.endswith('/ping')):
            return response

        response_status = response.status
        if response.content_type in {'application/json', 'application/problem+json'}:
            response_data = response.json
            # Don't display secrets in logs.
            for k in response_data:
                if k in {'access_token', 'refresh_token'}:
                    response_data[k] = '***'
        else:
            response_data = response.data

        logger.debug(
            f'{response_status=} {response_data=}',
        )

    except Exception:
        logger.exception('Failed to log response (DEBUG logging)')

    return response


def problem_response(*args, **kwargs):
    connexion_response = problem(*args, **kwargs)

    return Response(
        response=json.dumps(connexion_response.body, indent=2),
        status=connexion_response.status_code,
        content_type=connexion_response.mimetype,
        headers=connexion_response.headers,
    )


def db_integrity_error_handler(ex: sqlalchemy.exc.IntegrityError):
    try:
        if isinstance(ex.orig, (psycopg2.errors.UniqueViolation,
                                psycopg2.errors.ForeignKeyViolation)):
            msg = ex.orig.diag.message_detail
            return problem_response(400, 'Bad Request', msg)
    except Exception:
        pass

    logger.exception(ex)
    return problem_response(500, 'Internal Server Error',
                            'Unknown database integrity error.')


def value_error_handler(ex: ValueError):
    from rhub.api.utils import ModelValueError

    ext = {}
    if isinstance(ex, ModelValueError) and ex.attr_name:
        ext['invalid_field'] = ex.attr_name

    return problem_response(400, 'Bad Request', str(ex), ext=ext)


def create_app(extra_config=None):
    """Create Connexion/Flask application."""
    from . import _config

    if _config.LOGGING_CONFIG:
        logging.config.dictConfig(_config.LOGGING_CONFIG)
    else:
        try:
            import coloredlogs
            coloredlogs.install(level=_config.LOGGING_LEVEL)
        except ImportError:
            logger.addHandler(flask.logging.default_handler)
            logger.setLevel(_config.LOGGING_LEVEL)

    connexion_app = connexion.App(__name__)

    flask_app = connexion_app.app
    flask_app.url_map.strict_slashes = False
    if os.getenv('PROMETHEUS_MULTIPROC_DIR'):
        GunicornInternalPrometheusMetrics(flask_app)

    flask_app.config.from_object(_config)
    if extra_config:
        flask_app.config.from_mapping(extra_config)

    parser = prance.ResolvingParser(str(ROOT_PKG_PATH / 'openapi' / 'openapi.yml'))
    connexion_app.add_api(
        parser.specification,
        validate_responses=True,
        strict_validation=True,
        pythonic_params=True,
    )

    connexion_app.add_error_handler(ValueError, value_error_handler)
    connexion_app.add_error_handler(sqlalchemy.exc.IntegrityError,
                                    db_integrity_error_handler)

    # Enable CORS (Cross-Origin Resource Sharing)
    # https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS
    CORS(flask_app)

    flask_app.cli.add_command(init_command)
    flask_app.cli.add_command(create_user_command)
    flask_app.cli.add_command(create_token_command)

    if logger.isEnabledFor(logging.DEBUG):
        flask_app.before_request(log_request)
        flask_app.after_request(log_response)

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
            VaultModule(flask_app),
            SchedulerModule(flask_app),
            MessagingModule(flask_app),
            LdapModule(flask_app),
        ],
    )

    return flask_app
