import functools
import pathlib
import tempfile

import injector
import psycopg2.errors
import pytest
import sqlalchemy.exc

from rhub.api import create_app
from rhub.api.vault import Vault
from rhub.messaging import Messaging


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmp:
        yield pathlib.Path(tmp)


@pytest.fixture
def di_mock(mocker, vault_mock, messaging_mock):
    class TestsInjector(injector.Injector):
        def get(self, interface, *args, **kwargs):
            if interface is Vault:
                return vault_mock
            elif interface is Messaging:
                return messaging_mock
            return super().get(interface, *args, **kwargs)

    di = TestsInjector()
    mocker.patch('rhub.api.di', new=di)
    yield di


@pytest.fixture(autouse=True)
def vault_mock(mocker):
    vault_mock = mocker.Mock(spec=Vault)

    m = mocker.patch('rhub.api.vault.VaultModule._create_vault')
    m.return_value = vault_mock

    yield vault_mock


@pytest.fixture(autouse=True)
def messaging_mock(mocker):
    messaging_mock = mocker.Mock(spec=Messaging)

    m = mocker.patch('rhub.messaging.MessagingModule._create_messaging')
    m.return_value = messaging_mock

    yield messaging_mock


@pytest.fixture(autouse=True)
def auth_mock(mocker):
    user_data = {'uid': 1}
    mocker.patch('rhub.api.auth.security.basic_auth').return_value = user_data
    mocker.patch('rhub.auth.utils.is_user_in_group').return_value = True
    yield user_data


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
def client(mocker):
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
    scheduler_mock = session_mocker.Mock()

    m = session_mocker.patch('rhub.scheduler.SchedulerModule._create_scheduler')
    m.return_value = scheduler_mock

    yield scheduler_mock


@pytest.fixture(autouse=True)
def validate_hostname_mock(mocker):
    m = mocker.patch('rhub.api.utils.validate_hostname')
    m.return_value = True
    yield m
