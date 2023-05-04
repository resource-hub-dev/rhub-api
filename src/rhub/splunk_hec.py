import json
import logging
import urllib.request
import socket


def _json_serializer(value):
    if isinstance(value, (set, frozenset, range)):
        return list(value)
    return repr(value)


class SplunkHecHandler(logging.Handler):
    # http://docs.python.org/library/logging.html#logrecord-attributes
    _logrecord_attrs = {
        'args', 'asctime', 'created', 'exc_info', 'exc_text', 'filename',
        'funcName', 'id', 'levelname', 'levelno', 'lineno', 'module',
        'msecs', 'msecs', 'message', 'msg', 'name', 'pathname', 'process',
        'processName', 'relativeCreated', 'thread', 'threadName', 'extra',
        'auth_token', 'password', 'stack_info',
    }

    def __init__(self, base_url, token, source=None, sourcetype=None, index=None,
                 fields=None, host=None):
        super().__init__()

        self.base_url = base_url.rstrip('/')
        self.token = token
        self.source = source
        self.sourcetype = sourcetype
        self.index = index
        self.fields = fields or []
        self.host = host or socket.gethostname()

        self.request(f'{self.endpoint_url}/health')

    @property
    def endpoint_url(self):
        return f'{self.base_url}/services/collector'

    def request(self, url, method=None, data=None):
        # Using `requests` library could lead to infinite recursion because it
        # produces DEBUG logs.
        # While sending a log, N more logs are produced that also need to be
        # send which would generate N^2 logs ...
        request = urllib.request.Request(url, method=method, data=data)
        request.add_header('Authorization', f'Splunk {self.token}')
        return urllib.request.urlopen(request).read()

    def get_event(self, record):
        data = {
            'message': self.format(record),
            'level': record.levelname,
        }

        fields = {
            k: v for k, v in record.__dict__.items()
            if k not in self._logrecord_attrs or k in self.fields
        }

        event = {
            'event': data,
            'fields': fields,
            'time': record.created,
            'host': self.host,
        }

        if self.source:
            event['source'] = self.source

        if self.sourcetype:
            event['sourcetype'] = self.sourcetype

        if self.index:
            event['index'] = self.index

        return event

    def emit(self, record):
        try:
            data = json.dumps(
                self.get_event(record),
                default=_json_serializer,
                skipkeys=True,
            )
            self.request(
                f'{self.endpoint_url}/event',
                method='POST',
                data=data.encode(),
            )
        except RecursionError:
            raise
        except Exception:
            self.handleError(record)
