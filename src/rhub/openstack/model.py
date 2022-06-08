from sqlalchemy.dialects import postgresql

from rhub.api import db, di
from rhub.api.utils import ModelMixin
from rhub.auth.keycloak import KeycloakClient


class Cloud(db.Model, ModelMixin):
    __tablename__ = 'openstack_cloud'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False, default='')
    owner_group_id = db.Column(postgresql.UUID, nullable=False)
    url = db.Column(db.String(256), nullable=False)
    #: OpenStack credentials path in Vault
    credentials = db.Column(db.String(256), nullable=False)
    domain_name = db.Column(db.String(64), nullable=False)
    domain_id = db.Column(db.String(64), nullable=False)
    #: Network providers that can be used in the cloud
    networks = db.Column(db.ARRAY(db.String(64)), nullable=False)

    @property
    def owner_group_name(self):
        return di.get(KeycloakClient).group_get(self.owner_group_id)['name']

    def to_dict(self):
        data = super().to_dict()
        data['owner_group_name'] = self.owner_group_name
        return data
