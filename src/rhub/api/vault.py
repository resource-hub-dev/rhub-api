import logging
import abc

import hvac
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
        self._client.write(path, **data)


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
        return self._data.get(path)

    def write(self, path, data):
        self._data[path] = data
        with open(self._datafile, 'w') as f:
            self._data = yaml.safe_dump(self._data, f)
