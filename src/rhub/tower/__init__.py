from rhub.api import db
from rhub.tower import model, client  # noqa: F401


def init():
    db.create_all()
