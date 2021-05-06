import tempfile
import pathlib
import functools

import pytest

from rhub.api import create_app


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmp:
        yield pathlib.Path(tmp)


@pytest.fixture(autouse=True)
def vault_mock(mocker):
    vault_mock = mocker.Mock()
    vault_mock.read.return_value = {
        'username': 'username',
        'password': 'password',
    }

    mocker.patch('rhub.api.get_vault', new=vault_mock)

    yield vault_mock


@pytest.fixture(autouse=True)
def token_mock(mocker):
    decode_token_mock = mocker.patch(f'rhub.api.auth.token.decode_token')
    decode_token_mock.return_value = {
        'sub': '00000000-0000-0000-0000-000000000000',
        'scope': 'tests',
    }
    yield decode_token_mock


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
