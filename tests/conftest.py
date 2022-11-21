import functools
import pathlib
import tempfile

import psycopg2.errors
import pytest
import sqlalchemy.exc

from rhub.api import create_app
from rhub.api.vault import Vault
from rhub.auth.keycloak import KeycloakClient
from rhub.messaging import Messaging


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmp:
        yield pathlib.Path(tmp)


@pytest.fixture(autouse=True, scope='session')
def keycloak_mock(session_mocker):
    keycloak_mock = session_mocker.Mock(spec=KeycloakClient)
    keycloak_mock.user_check_role.return_value = True

    m = session_mocker.patch('rhub.auth.keycloak.KeycloakModule._create_keycloak')
    m.return_value = keycloak_mock

    yield keycloak_mock


@pytest.fixture(autouse=True, scope='session')
def vault_mock(session_mocker):
    vault_mock = session_mocker.Mock(spec=Vault)

    m = session_mocker.patch('rhub.api.vault.VaultModule._create_vault')
    m.return_value = vault_mock

    yield vault_mock


@pytest.fixture(autouse=True, scope='session')
def messaging_mock(session_mocker):
    messaging_mock = session_mocker.Mock(spec=Messaging)

    m = session_mocker.patch('rhub.messaging.MessagingModule._create_messaging')
    m.return_value = messaging_mock

    yield messaging_mock


@pytest.fixture(autouse=True)
def auth_mock(mocker):
    m = mocker.patch(f'rhub.api.auth.security.basic_auth')
    m.return_value = {'uid': 1}
    yield m


@pytest.fixture(autouse=True, scope='function')
def db_query_mock(mocker):
    def query_property_get(self, obj, objtype):
        # Descriptor __get__ implementation to return mocks
        if not hasattr(self, '_mocks'):
            self._mocks = {}
        if objtype not in self._mocks:
            self._mocks[objtype] = mocker.Mock()
        return self._mocks[objtype]

    query_property_mock = mocker.patch('flask_sqlalchemy._QueryProperty.__get__')
    query_property_mock.side_effect = query_property_get


@pytest.fixture(autouse=True)
def db_session_mock(mocker):
    yield mocker.patch('rhub.api.db.session')


@pytest.fixture
def db_unique_violation(mocker, db_session_mock):
    class UniqueViolationMock(mocker.Mock, sqlalchemy.exc.IntegrityError):
        def __init__(self, name, value):
            super().__init__()
            self.orig = mocker.Mock(spec=psycopg2.errors.UniqueViolation)
            self.orig.diag = mocker.Mock(spec=psycopg2.extensions.Diagnostics)
            self.orig.diag.message_detail = f'Key ({name})=({value}) already exists.'

    def factory(name, value):
        side_effect = UniqueViolationMock(name, value)
        db_session_mock.flush.side_effect = side_effect
        db_session_mock.commit.side_effect = side_effect

    yield factory


@pytest.fixture
def db_foreign_key_violation(mocker, db_session_mock):
    class FkViolationMock(mocker.Mock, sqlalchemy.exc.IntegrityError):
        def __init__(self, name, value, table):
            super().__init__()
            self.orig = mocker.Mock(spec=psycopg2.errors.ForeignKeyViolation)
            self.orig.diag = mocker.Mock(spec=psycopg2.extensions.Diagnostics)
            self.orig.diag.message_detail = f'Key ({name})=({value}) is not present in table "{table}".'

    def factory(name, value, table):
        side_effect = FkViolationMock(name, value, table)
        db_session_mock.flush.side_effect = side_effect
        db_session_mock.commit.side_effect = side_effect

    yield factory


@pytest.fixture
def client(mocker, temp_dir):
    mocker.patch.dict('os.environ', {
        'RHUB_DB_TYPE': 'postgresql',
        'RHUB_DB_HOST': 'localhost',
        'RHUB_DB_PORT': '5432',
        'RHUB_DB_USERNAME': 'test',
        'RHUB_DB_PASSWORD': 'test',
        'RHUB_DB_DATABASE': 'test',
    })

    app = create_app()
    with app.test_client() as client:
        yield client


@pytest.fixture(autouse=True, scope='session')
def scheduler_mock(session_mocker):
    scheduler_mock = session_mocker.Mock(spec=Vault)

    m = session_mocker.patch('rhub.scheduler.SchedulerModule._create_scheduler')
    m.return_value = scheduler_mock

    yield scheduler_mock


@pytest.fixture(autouse=True)
def validate_hostname_mock(mocker):
    m = mocker.patch('rhub.api.utils.validate_hostname')
    m.return_value = True
    yield m
