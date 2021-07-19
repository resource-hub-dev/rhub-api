import logging
import abc

import hvac
import yaml


logger = logging.getLogger(__name__)


class Vault(abc.ABC):
    @abc.abstractmethod
    def read(self, path):
        raise NotImplementedError


class HashicorpVault(Vault):
    """Hashicorp Vault client."""

    def __init__(self, url, role_id, secret_id):
        self._client = hvac.Client(url)
        self._client.auth.approle.login(role_id=role_id, secret_id=secret_id)

    def read(self, path):
        mount_point, path = path.split('/', 1)
        try:
            secret = self._client.secrets.kv.v1.read_secret(
                path=path,
                mount_point=mount_point,
            )
            return secret['data']
        except hvac.exceptions.InvalidPath:
            return None


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
        with open(datafile) as f:
            self._data = yaml.safe_load(f)

    def read(self, path):
        return self._data.get(path)
