import logging

import openstack
from sqlalchemy.orm import validates

from rhub.api import db, di, utils
from rhub.api.utils import ModelMixin, ModelValueError
from rhub.api.vault import Vault
from rhub.auth import model as auth_model


logger = logging.getLogger(__name__)


class Cloud(db.Model, ModelMixin):
    __tablename__ = 'openstack_cloud'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False, default='')
    owner_group_id = db.Column(db.ForeignKey('auth_group.id'), nullable=False)
    owner_group = db.relationship(auth_model.Group)
    url = db.Column(db.String(256), nullable=False)
    #: OpenStack credentials path in Vault
    credentials = db.Column(db.String(256), nullable=False)
    domain_name = db.Column(db.String(64), nullable=False)
    domain_id = db.Column(db.String(64), nullable=False)
    #: Network providers that can be used in the cloud
    networks = db.Column(db.ARRAY(db.String(64)), nullable=False)

    #: :type: list of :class:`Project`
    projects = db.relationship('Project', back_populates='cloud')

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

    @validates('url')
    def _validate_url(self, key, value):
        if not utils.validate_url(value):
            raise ModelValueError(f'URL {value!r} is not valid.',
                                  self, key, value)
        return value


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
    owner_id = db.Column(db.ForeignKey('auth_user.id'), nullable=False)
    owner = db.relationship(auth_model.User)
    group_id = db.Column(db.ForeignKey('auth_group.id'), nullable=True)
    group = db.relationship(auth_model.Group)

    def to_dict(self):
        data = super().to_dict()
        data['cloud_name'] = self.cloud.name
        data['owner_name'] = self.owner.name
        data['group_name'] = self.group.name if self.group else None
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
