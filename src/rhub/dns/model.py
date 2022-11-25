from sqlalchemy.orm import validates

from rhub.api import db, di, utils
from rhub.api.utils import ModelMixin, ModelValueError
from rhub.api.vault import Vault
from rhub.auth import model as auth_model


class DnsServer(db.Model, ModelMixin):
    __tablename__ = 'dns_server'
    __table_args__ = (
        db.UniqueConstraint('hostname', 'zone', name='ix_dns_server_zone'),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False, default='')
    owner_group_id = db.Column(db.ForeignKey('auth_group.id'), nullable=False)
    owner_group = db.relationship(auth_model.Group)
    hostname = db.Column(db.String(256), nullable=False)
    zone = db.Column(db.String(256), nullable=False)
    #: nsupdate key
    credentials = db.Column(db.String(256), nullable=False)

    def to_dict(self):
        data = super().to_dict()
        data['owner_group_name'] = self.owner_group.name
        return data

    @validates('credentials')
    def _validate_credentials(self, key, value):
        vault = di.get(Vault)
        if not vault.exists(value):
            raise ModelValueError(f'{value!r} does not exist in Vault',
                                  self, key, value)
        return value

    @validates('hostname')
    def _validate_hostname(self, key, value):
        if not utils.validate_hostname(value):
            raise ModelValueError(f'Hostname {value!r} is not valid.',
                                  self, key, value)
        return value
