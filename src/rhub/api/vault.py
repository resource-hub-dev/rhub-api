import abc
import logging

import hvac
import injector
import yaml


logger = logging.getLogger(__name__)


class Vault(abc.ABC):
    @abc.abstractmethod
    def read(self, path):
        raise NotImplementedError

    @abc.abstractmethod
    def write(self, path, data):
        raise NotImplementedError


class HashicorpVault(Vault):
    """Hashicorp Vault client."""

    def __init__(self, url, role_id, secret_id):
        self._client = hvac.Client(url)
        self._client.auth.approle.login(role_id=role_id, secret_id=secret_id)

    def read(self, path):
        logger.debug(f'Reading credentials from {self!r} at path {path!r}')
        try:
            secret = self._client.read(path)
            # Check if response is kv-v2
            if 'data' in secret['data'] and 'metadata' in secret['data']:
                return secret['data']['data']
            return secret['data']
        except hvac.exceptions.InvalidPath:
            logger.exception(f'Failed to get credentials from {path!r}')
            return None

    def write(self, path, data):
        logger.debug(f'Writing credentials to {self!r} at path {path!r}')
        self._client.write(path, **data)

    def __repr__(self):
        return f'HashiCorpVault({self._client.url})'


class FileVault(Vault):
    """
    **Insecure** vault that reads credentials from YAML file.

    YAML file structure is mapping 'credential path' -> 'data object', example ::

        kv/example/prod:
            username: user
            password: pass
        kv/example/stage:
            username: foo
            password: bar
    """

    def __init__(self, datafile):
        logger.warning(
            'Storing secrets in plaintext YAML files is INSECURE!! '
            'Use Hashicorp Vault in production!'
        )
        self._datafile = datafile
        with open(self._datafile) as f:
            self._data = yaml.safe_load(f)

    def read(self, path):
        logger.debug(f'Reading credentials from {self!r} at path {path!r}')
        return self._data.get(path)

    def write(self, path, data):
        logger.debug(f'Writing credentials to {self!r} at path {path!r}')
        self._data[path] = data
        with open(self._datafile, 'w') as f:
            yaml.safe_dump(self._data, f)

    def __repr__(self):
        return f'FileVault({self._datafile})'


class VaultModule(injector.Module):
    def __init__(self, app):
        self.app = app

    def configure(self, binder):
        try:
            binder.bind(
                Vault,
                to=self._create_vault(),
                scope=injector.singleton,
            )
        except Exception:
            logger.exception(
                'Failed to create Vault client. Some endpoints may not work.'
            )

    def _create_vault(self):
        vault_type = self.app.config['VAULT_TYPE']

        if vault_type == 'hashicorp':
            return HashicorpVault(
                url=self.app.config['VAULT_ADDR'],
                role_id=self.app.config['VAULT_ROLE_ID'],
                secret_id=self.app.config['VAULT_SECRET_ID'],
            )

        elif vault_type == 'file':
            return FileVault(self.app.config['VAULT_PATH'])

        logger.error(f'Unknown vault type {vault_type}')
        raise Exception(f'Unknown vault type {vault_type}')
