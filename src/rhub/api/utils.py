import datetime

from rhub.api import db


class ModelMixin:
    """Datatabase model mixin with methods useful in REST API endpoints."""

    def to_dict(self):
        """Covert to `dict`."""
        data = {}
        for column in self.__table__.columns:
            data[column.name] = getattr(self, column.name)
        return data

    @classmethod
    def from_dict(cls, data):
        """Create from `dict`."""
        return cls(**data)

    def update_from_dict(self, data):
        """Update from `dict`."""
        for k, v in data.items():
            setattr(self, k, v)


def date_now():
    return datetime.datetime.now().astimezone(datetime.timezone.utc)


def db_sort(query, sort_by):
    direction = 'DESC' if sort_by.startswith('-') else 'ASC'
    column = sort_by.removeprefix('-')
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
