from sqlalchemy.dialects import postgresql

from rhub.api import db, di
from rhub.api.utils import ModelMixin
from rhub.auth.keycloak import KeycloakClient


class SatelliteServer(db.Model, ModelMixin):
    __tablename__ = 'satellite_server'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False, default='')
    owner_group_id = db.Column(postgresql.UUID, nullable=False)
    hostname = db.Column(db.String(256), unique=True, nullable=False)
    insecure = db.Column(db.Boolean, default=False, nullable=False)
    credentials = db.Column(db.String(256), nullable=False)

    @property
    def owner_group_name(self):
        return di.get(KeycloakClient).group_get_name(self.owner_group_id)

    def to_dict(self):
        data = super().to_dict()
        data['owner_group_name'] = self.owner_group_name
        return data
