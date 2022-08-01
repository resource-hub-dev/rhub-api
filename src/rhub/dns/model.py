from sqlalchemy.dialects import postgresql

from rhub.api import db, di
from rhub.api.utils import ModelMixin
from rhub.auth.keycloak import KeycloakClient


class DnsServer(db.Model, ModelMixin):
    __tablename__ = 'dns_server'
    __table_args__ = (
        db.UniqueConstraint('hostname', 'zone', name='ix_dns_server_zone'),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False, default='')
    owner_group_id = db.Column(postgresql.UUID, nullable=False)
    hostname = db.Column(db.String(256), nullable=False)
    zone = db.Column(db.String(256), nullable=False)
    #: nsupdate key
    credentials = db.Column(db.String(256), nullable=False)

    @property
    def owner_group_name(self):
        return di.get(KeycloakClient).group_get_name(self.owner_group_id)

    def to_dict(self):
        data = super().to_dict()
        data['owner_group_name'] = self.owner_group_name
        return data
