import datetime


def row2dict(row):
    """Convert SQLAlchemy row to dict."""
    if hasattr(row, 'to_dict'):
        return row.to_dict()
    d = {}
    for column in row.__table__.columns:
        d[column.name] = getattr(row, column.name)
    return d


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
