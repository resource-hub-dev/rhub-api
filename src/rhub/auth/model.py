import hashlib
import secrets

from sqlalchemy.dialects import postgresql

from rhub.api import db
from rhub.api.utils import ModelMixin


class User(db.Model, ModelMixin):
    __tablename__ = 'auth_user'

    id = db.Column(db.Integer, primary_key=True)
    external_uuid = db.Column(postgresql.UUID, nullable=True)
    name = db.Column(db.String(64), unique=True, nullable=True)
    email = db.Column(db.String(128), nullable=True)

    groups = db.relationship('Group', secondary='auth_user_group')
    tokens = db.relationship('Token', back_populates='user',
                             cascade='all,delete-orphan')

    @property
    def is_external(self):
        return self.external_uuid is not None


class Token(db.Model, ModelMixin):
    __tablename__ = 'auth_token'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.ForeignKey('auth_user.id'), nullable=False)
    user = db.relationship('User', back_populates='tokens')
    token = db.Column(db.String(64), nullable=False, index=True)

    @classmethod
    def generate(cls, **kwargs):
        cleartext = secrets.token_urlsafe(32)
        kwargs['token'] = hashlib.sha256(cleartext.encode()).hexdigest()
        return cleartext, cls(**kwargs)

    @classmethod
    def find(cls, cleartext):
        token = hashlib.sha256(cleartext.encode()).hexdigest()
        q = cls.query.filter(cls.token == token)
        if q.count() != 1:
            return None
        return q.first()

    def to_dict(self):
        data = super().to_dict()
        del data['user_id']
        del data['token']
        return data


class Group(db.Model, ModelMixin):
    __tablename__ = 'auth_group'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)

    users = db.relationship('Group', secondary='auth_user_group')


class UserGroup(db.Model):
    __tablename__ = 'auth_user_group'

    user_id = db.Column(db.ForeignKey('auth_user.id'), primary_key=True)
    group_id = db.Column(db.ForeignKey('auth_group.id'), primary_key=True)
