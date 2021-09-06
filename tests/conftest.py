import tempfile
import pathlib
import functools

import pytest

from rhub.api import create_app
from rhub.auth.keycloak import KeycloakClient


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmp:
        yield pathlib.Path(tmp)


@pytest.fixture(autouse=True)
def vault_mock(mocker):
    vault_mock = mocker.Mock()
    mocker.patch('rhub.api.get_vault').return_value = vault_mock
    yield vault_mock


@pytest.fixture(autouse=True)
def token_mock(mocker):
    decode_token_mock = mocker.patch(f'rhub.api.auth.token.decode_token')
    decode_token_mock.return_value = {
        'sub': '00000000-0000-0000-0000-000000000000',
        'scope': 'tests',
    }
    yield decode_token_mock


@pytest.fixture(autouse=True)
def user_role_check_mock(mocker):
    keycloak_mock = mocker.Mock(spec=KeycloakClient)

    get_keycloak_mock = mocker.patch(f'rhub.auth.utils.get_keycloak')
    get_keycloak_mock.return_value = keycloak_mock

    keycloak_mock.user_check_role.return_value = True

    yield keycloak_mock.user_check_role


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
def client(mocker, temp_dir):
    mocker.patch.dict('os.environ', {
        'DB_TYPE': 'postgresql',
        'DB_HOST': 'localhost',
        'DB_PORT': '5432',
        'DB_USERNAME': 'test',
        'DB_PASSWORD': 'test',
        'DB_DATABASE': 'test',
    })

    app = create_app()
    with app.test_client() as client:
        yield client

@pytest.fixture(autouse=True)
def scheduler_mock(mocker):
    yield mocker.patch('rhub.api.sched')
