import openstack
from sqlalchemy.dialects import postgresql

from rhub.api import db, di
from rhub.api.utils import ModelMixin
from rhub.api.vault import Vault
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

    #: :type: list of :class:`Project`
    projects = db.relationship('Project', back_populates='cloud')

    @property
    def owner_group_name(self):
        return di.get(KeycloakClient).group_get(self.owner_group_id)['name']

    def to_dict(self):
        data = super().to_dict()
        data['owner_group_name'] = self.owner_group_name
        return data


class Project(db.Model, ModelMixin):
    __tablename__ = 'openstack_project'
    __table_args__ = (
        db.UniqueConstraint('cloud_id', 'name', name='ix_cloud_project'),
    )

    id = db.Column(db.Integer, primary_key=True)

    cloud_id = db.Column(db.Integer, db.ForeignKey('openstack_cloud.id'),
                         nullable=False)
    #: :type: :class:`Cloud`
    cloud = db.relationship('Cloud', back_populates='projects')

    name = db.Column(db.String(64), nullable=False)
    description = db.Column(db.Text, nullable=False, default='')
    owner_id = db.Column(postgresql.UUID, nullable=False)
    group_id = db.Column(postgresql.UUID, nullable=True)

    @property
    def owner_name(self):
        return di.get(KeycloakClient).user_get(self.owner_id)['username']

    @property
    def group_name(self):
        if self.group_id:
            return di.get(KeycloakClient).group_get(self.group_id)['name']
        return None

    def to_dict(self):
        data = super().to_dict()
        data['cloud_name'] = self.cloud.name
        data['owner_name'] = self.owner_name
        data['group_name'] = self.group_name
        return data

    def create_openstack_client(self):
        """
        Create OpenStack SDK connection (client) for the project.

        Returns:
            openstack.connection.Connection
        """
        vault = di.get(Vault)
        credentials = vault.read(self.cloud.credentials)
        if not credentials:
            raise RuntimeError(
                f'Missing credentials in vault; {vault!r} {self.cloud.credentials}'
            )
        connection = openstack.connection.Connection(
            auth=dict(
                auth_url=self.cloud.url,
                username=credentials['username'],
                password=credentials['password'],
                project_name=self.name,
                domain_name=self.cloud.domain_name,
            ),
            region_name="regionOne",
            interface="public",
            identity_api_version=3,
        )
        connection.authorize()
        return connection

    def get_openstack_limits(self):
        os_client = self.create_openstack_client()
        return os_client.compute.get_limits()
