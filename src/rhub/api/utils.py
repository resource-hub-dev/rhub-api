import copy
import datetime
import socket
import urllib.parse

from sqlalchemy.inspection import inspect
from sqlalchemy.orm import declarative_mixin, declared_attr
from sqlalchemy.sql import functions

from rhub.api import db


class ModelMixin:
    """Database model mixin with methods useful in REST API endpoints."""

    __embedded__ = []       # read-write embedding
    __embedded_ro__ = []    # read-only embedding

    def to_dict(self):
        """Covert a model's object to `dict`, with parent's columns."""
        data = {}

        for column in inspect(self.__class__).columns:
            data[column.name] = getattr(self, column.name)

        for embedded_name in self.__embedded__ + self.__embedded_ro__:
            if getattr(self, embedded_name):
                data[embedded_name] = getattr(self, embedded_name).to_dict()
            else:
                data[embedded_name] = None

        return data

    @classmethod
    def from_dict(cls, data):
        """Create from `dict`."""
        data = copy.deepcopy(data)

        for embedded_name in cls.__embedded__:
            embedded_cls = db.inspect(cls).relationships[embedded_name].mapper.class_
            embedded_data = data.pop(embedded_name, None)
            if embedded_data:
                data[embedded_name] = embedded_cls.from_dict(embedded_data)

        return cls(**data)

    def update_from_dict(self, data):
        """Update from `dict`."""
        data = copy.deepcopy(data)

        for embedded_name in self.__embedded__:
            if embedded_name not in data:
                continue

            embedded_cls = db.inspect(self.__class__).relationships[embedded_name].mapper.class_
            embedded_data = data.pop(embedded_name, None)

            if embedded_data:
                if getattr(self, embedded_name) is None:
                    setattr(self, embedded_name, embedded_cls.from_dict(embedded_data))
                else:
                    getattr(self, embedded_name).update_from_dict(embedded_data)
            else:
                old_embedded_data = getattr(self, embedded_name)
                setattr(self, embedded_name, None)
                if old_embedded_data is not None:
                    db.session.delete(old_embedded_data)
                    db.session.flush()

        for k, v in data.items():
            setattr(self, k, v)


class ModelValueError(ValueError):
    def __init__(self, msg, row=None, attr_name=None, attr_value=None):
        super().__init__(msg)
        self.row = row
        self.attr_name = attr_name
        self.attr_value = attr_value


def validate_hostname(hostname):
    """Check if hostname is valid."""
    try:
        socket.getaddrinfo(hostname, None)
        return True
    except Exception:
        return False


def validate_url(url):
    try:
        parsed_url = urllib.parse.urlparse(url)
        return validate_hostname(parsed_url.hostname)
    except Exception:
        return False


def date_now():
    return datetime.datetime.now().astimezone(datetime.timezone.utc)


def db_sort(query, sort_by, column_remap=None):
    direction = 'DESC' if sort_by.startswith('-') else 'ASC'
    column = sort_by.removeprefix('-')

    if column_remap and column in column_remap:
        column = column_remap[column]

    return query.order_by(db.text(f'{column} {direction}'))


def condition_eval(expr, params):
    """
    Evaluate condition expression.

    ["not", <expr>]
    ["and", <expr...>]
    ["or", <expr...>]
    ["param_eq", <param-name>, <value>]
    ["param_ne", <param-name>, <value>]
    ["param_lt", <param-name>, <value>]
    ["param_gt", <param-name>, <value>]
    ["param_in", <param-name>, <value>]
    """
    if expr[0] == 'not':
        return not condition_eval(expr[1], params)
    elif expr[0] == 'and':
        return all(condition_eval(i, params) for i in expr[1:])
    elif expr[0] == 'or':
        return any(condition_eval(i, params) for i in expr[1:])
    if expr[0] == 'param_eq':
        return params.get(expr[1]) == expr[2]
    elif expr[0] == 'param_ne':
        return params.get(expr[1]) != expr[2]
    elif expr[0] == 'param_lt':
        return expr[1] in params and params[expr[1]] < expr[2]
    elif expr[0] == 'param_gt':
        return expr[1] in params and params[expr[1]] > expr[2]
    elif expr[0] == 'param_in':
        return expr[1] in params and expr[2] in params[expr[1]]
    raise ValueError(f'Unknown operation {expr[0]!r}')


@declarative_mixin
class TimestampMixin:
    @declared_attr
    def created_at(cls):
        return db.Column(
            db.DateTime(timezone=True),
            server_default=functions.now(),
            nullable=False,
        )

    @declared_attr
    def updated_at(cls):
        return db.Column(
            db.DateTime(timezone=True),
            server_default=functions.now(),
            nullable=False,
            server_onupdate=functions.now(),  # TODO: why is alembic ignoring this?
        )
