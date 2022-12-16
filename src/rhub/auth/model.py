import hashlib
import secrets

from sqlalchemy.dialects import postgresql

from rhub.api import db
from rhub.api.utils import ModelMixin, TimestampMixin
from rhub.auth import ldap


class User(db.Model, ModelMixin, TimestampMixin):
    __tablename__ = 'auth_user'

    id = db.Column(db.Integer, primary_key=True)
    external_uuid = db.Column(postgresql.UUID, nullable=True)
    name = db.Column(db.String(64), unique=True, nullable=True)
    email = db.Column(db.String(128), nullable=True)
    ssh_keys = db.Column(db.ARRAY(db.Text), server_default='{}', nullable=False)

    ldap_dn = db.Column(db.String(256), nullable=True)

    groups = db.relationship('Group', secondary='auth_user_group')
    tokens = db.relationship('Token', back_populates='user',
                             cascade='all,delete-orphan')

    @property
    def is_external(self):
        return self.external_uuid is not None

    @classmethod
    def create_from_ldap(cls, ldap_client: ldap.LdapClient, external_uuid):
        user_data = ldap_client.get_user_by_uuid(external_uuid)
        user_data['external_uuid'] = external_uuid

        user_groups = user_data.pop('groups')
        user_groups_dn = [i['ldap_dn'] for i in user_groups]
        user_groups_in_db = Group.query.filter(Group.ldap_dn.in_(user_groups_dn)).all()

        user_data['groups'] = user_groups_in_db

        return cls.from_dict(user_data)

    def update_from_ldap(self, ldap_client: ldap.LdapClient):
        user_data = ldap_client.get_user_by_uuid(self.external_uuid)

        user_groups = user_data.pop('groups')
        user_groups_dn = [i['ldap_dn'] for i in user_groups]
        user_groups_in_db = Group.query.filter(Group.ldap_dn.in_(user_groups_dn)).all()

        for group in user_groups_in_db:
            if group not in self.groups:
                self.groups.append(group)

        for group in list(self.groups):
            if group.ldap_dn and group.ldap_dn not in user_groups_dn:
                self.groups.remove(group)

        self.update_from_dict(user_data)


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

    ldap_dn = db.Column(db.String(256), nullable=True)

    users = db.relationship('User', secondary='auth_user_group')


class UserGroup(db.Model):
    __tablename__ = 'auth_user_group'

    user_id = db.Column(db.ForeignKey('auth_user.id'), primary_key=True)
    group_id = db.Column(db.ForeignKey('auth_group.id'), primary_key=True)
