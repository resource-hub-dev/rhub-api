import datetime
import copy
import enum
import re

from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import validates

from rhub.api import db, get_vault
from rhub.api.utils import ModelMixin
from rhub.tower.client import Tower


class Region(db.Model, ModelMixin):
    __tablename__ = 'lab_region'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), unique=True, nullable=False)
    location = db.Column(db.String(32), index=True, nullable=True)
    description = db.Column(db.Text, nullable=False, default='')
    banner = db.Column(db.Text, nullable=False, default='')
    enabled = db.Column(db.Boolean, default=True)
    quota_id = db.Column(db.Integer, db.ForeignKey('lab_quota.id'),
                         nullable=True)
    #: :type: :class:`Quota`
    quota = db.relationship('Quota', uselist=False, back_populates='region')
    lifespan_length = db.Column(db.Integer, nullable=True)
    reservations_enabled = db.Column(db.Boolean, default=True)
    reservation_expiration_max = db.Column(db.Integer, nullable=True)
    owner_group = db.Column(postgresql.UUID, nullable=False)
    #: Limits use only to specific group of people. `NULL` == shared lab.
    users_group = db.Column(postgresql.UUID, nullable=True, index=True)
    ...  # TODO policies?
    tower_id = db.Column(db.Integer, db.ForeignKey('lab_tower.id'))
    #: :type: :class:`Tower`
    tower = db.relationship('Tower')

    openstack_url = db.Column(db.String(256), nullable=False)
    #: OpenStack credentials path in Vault
    openstack_credentials = db.Column(db.String(256), nullable=False)
    openstack_project = db.Column(db.String(64), nullable=False)
    openstack_domain_name = db.Column(db.String(64), nullable=False)
    openstack_domain_id = db.Column(db.String(64), nullable=False)
    #: Network providers that can be used in the region
    openstack_networks = db.Column(db.ARRAY(db.String(64)), nullable=False)
    #: SSH key name
    openstack_keyname = db.Column(db.String(64), nullable=False)

    satellite_hostname = db.Column(db.String(256), nullable=False)
    satellite_insecure = db.Column(db.Boolean, default=False, nullable=False)
    #: Satellite credentials path in Vault
    satellite_credentials = db.Column(db.String(256), nullable=False)

    dns_server_hostname = db.Column(db.String(256), nullable=False)
    dns_server_zone = db.Column(db.String(256), nullable=False)
    #: DNS server credentials path in Vault
    dns_server_key = db.Column(db.String(256), nullable=False)

    vault_server = db.Column(db.String(256), nullable=False)
    download_server = db.Column(db.String(256), nullable=False)

    #: :type: list of :class:`Cluster`
    clusters = db.relationship('Cluster', back_populates='region')

    _INLINE_CHILDS = ['openstack', 'satellite', 'dns_server']

    @property
    def lifespan_enabled(self):
        return self.lifespan_length is not None

    @property
    def lifespan_delta(self):
        """:type: :class:`datetime.timedelta` or `None`"""
        if not self.lifespan_length:
            return None
        return datetime.timedelta(days=self.lifespan_length)

    @property
    def reservation_expiration_max_delta(self):
        """:type: :class:`datetime.timedelta` or `None`"""
        if not self.reservation_expiration_max:
            return None
        return datetime.timedelta(days=self.reservation_expiration_max)

    def to_dict(self):
        data = {}

        for column in self.__table__.columns:
            if column.name == 'quota_id':
                continue
            for i in self._INLINE_CHILDS:
                if column.name.startswith(f'{i}_'):
                    if i not in data:
                        data[i] = {}
                    data[i][column.name[len(i) + 1:]] = getattr(self, column.name)
                    break
            else:
                data[column.name] = getattr(self, column.name)

        if self.quota:
            data['quota'] = self.quota.to_dict()
        else:
            data['quota'] = None

        return data

    @classmethod
    def from_dict(cls, data):
        data = copy.deepcopy(data)

        quota_data = data.pop('quota', None)
        if quota_data:
            data['quota'] = Quota.from_dict(quota_data)

        for i in cls._INLINE_CHILDS:
            for k, v in data[i].items():
                data[f'{i}_{k}'] = v
            del data[i]

        return super().from_dict(data)

    def update_from_dict(self, data):
        data = copy.deepcopy(data)

        if 'quota' in data:
            if data['quota']:
                if self.quota is None:
                    self.quota = Quota.from_dict(data['quota'])
                else:
                    self.quota.update_from_dict(data['quota'])
            else:
                self.quota = None
            del data['quota']

        for i in self._INLINE_CHILDS:
            if i in data:
                for k, v in data[i].items():
                    setattr(self, f'{i}_{k}', v)
                del data[i]

        super().update_from_dict(data)


class Quota(db.Model, ModelMixin):
    __tablename__ = 'lab_quota'

    id = db.Column(db.Integer, primary_key=True)
    num_vcpus = db.Column(db.Integer, nullable=True)
    ram_mb = db.Column(db.Integer, nullable=True)
    num_volumes = db.Column(db.Integer, nullable=True)
    volumes_gb = db.Column(db.Integer, nullable=True)

    #: :type: :class:`Region`
    region = db.relationship('Region', back_populates='quota',
                             cascade='all,delete-orphan')

    def to_dict(self):
        data = super().to_dict()
        del data['id']
        return data


class Tower(db.Model, ModelMixin):
    __tablename__ = 'lab_tower'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    enabled = db.Column(db.Boolean, default=True)
    url = db.Column(db.String(256), nullable=False)
    #: Credentials path in Vault
    credentials = db.Column(db.String(256), nullable=False)

    #: :type: list of :class:`Region`
    regions = db.relationship('Region', back_populates='tower',
                              cascade='all,delete-orphan')

    def create_tower_client(self) -> Tower:
        """
        Create Tower client.

        :returns: Tower
        :raises: RuntimeError if failed to create client due to missing
                 credentials in vault
        :raises: Exception any other errors
        """
        credentials = get_vault().read(self.credentials)
        if not credentials:
            raise RuntimeError('Missing credentials in vault')
        return Tower(
            url=self.url,
            username=credentials['username'],
            password=credentials['password'],
        )


class ClusterStatus(str, enum.Enum):
    ACTIVE = 'Active'
    PRE_PROVISIONING_QUEUED = 'Pre-Provisioning Queued'
    PRE_PROVISIONING = 'Pre-Provisioning'
    PRE_PROVISIONING_FAILED = 'Pre-Provisioning Failed'
    PROVISIONING_QUEUED = 'Provisioning Queued'
    PROVISIONING = 'Provisioning'
    PROVISIONING_FAILED = 'Provisioning Failed'
    POST_PROVISIONING_QUEUED = 'Post-Provisioning Queued'
    POST_PROVISIONING = 'Post-Provisioning'
    POST_PROVISIONING_FAILED = 'Post-Provisioning Failed'
    PRE_INSTALLATION_QUEUED = 'Pre-Installation Queued'
    PRE_INSTALLING = 'Pre-Installing'
    PRE_INSTALLATION_FAILED = 'Pre-Installation Failed'
    INSTALLATION_QUEUED = 'Installation Queued'
    INSTALLING = 'Installing'
    INSTALLATION_FAILED = 'Installation Failed'
    POST_INSTALLATION_QUEUED = 'Post-Installation Queued'
    POST_INSTALLING = 'Post-Installing'
    POST_INSTALLATION_FAILED = 'Post-Installation Failed'
    PRE_DELETION_QUEUED = 'Pre-Deletion Queued'
    PRE_DELETING = 'Pre-Deleting'
    PRE_DELETION_FAILED = 'Pre-Deletion Failed'
    DELETION_QUEUED = 'Deletion Queued'
    DELETING = 'Deleting'
    DELETION_FAILED = 'Deletion Failed'
    POST_DELETION_QUEUED = 'Post-Deletion Queued'
    POST_DELETING = 'Post-Deleting'
    POST_DELETION_FAILED = 'Post-Deletion Failed'
    DELETED = 'Deleted'


class Cluster(db.Model, ModelMixin):
    __tablename__ = 'lab_cluster'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False, default='')
    user_id = db.Column(postgresql.UUID, nullable=False)
    group_id = db.Column(postgresql.UUID, nullable=True)
    created = db.Column(db.DateTime(timezone=True))

    region_id = db.Column(db.Integer, db.ForeignKey('lab_region.id'),
                          nullable=False)
    #: :type: :class:`Region`
    region = db.relationship('Region', back_populates='clusters')

    reservation_expiration = db.Column(db.DateTime(timezone=True), nullable=True)
    #: Cluster lifespan expiration (hard-limit), see
    #: :meth:`Region.create_cluster`.
    lifespan_expiration = db.Column(db.DateTime(timezone=True), nullable=True)
    #: :type: :class:`ClusterStatus`
    status = db.Column(db.Enum(ClusterStatus), nullable=True, default=None)

    #: :type: list of :class:`ClusterEvent`
    events = db.relationship('ClusterEvent', back_populates='cluster',
                             cascade='all,delete-orphan')
    #: :type: list of :class:`ClusterHost`
    hosts = db.relationship('ClusterHost', back_populates='cluster',
                            cascade='all,delete-orphan')

    RESERVED_NAMES = [
        'localhost',
        'all',
        'ungrouped',
        'lab',
        'cluster',
        'region',
        'tower',
    ]

    @validates('name')
    def validate_name(self, key, value):
        if value.lower() in self.RESERVED_NAMES:
            raise ValueError(f'{value!r} is reserved name')
        if len(value) < 6:
            raise ValueError('Cluster name is too short')
        if len(value) > 20:
            raise ValueError('Cluster name is too long')
        if not re.match(r'^[0-9a-z]+$', value):
            raise ValueError(
                'Cluster name contains invalid characters, '
                'allowed are only 0-9 and a-z (uppercase characters are not allowed).'
            )
        return value

    @property
    def quota(self):
        """:type: :class:`Quota` or `None`"""
        if self.region:
            return self.region.quota
        return None

    def to_dict(self):
        data = super().to_dict()
        if self.quota:
            data['quota'] = self.quota.to_dict()
        if self.status:
            data['status'] = self.status.value
        else:
            data['status'] = None
        return data


class ClusterEventType(str, enum.Enum):
    TOWER_JOB = 'tower_job'
    RESERVATION_CHANGE = 'reservation_change'
    LIFESPAN_CHANGE = 'lifespan_change'


class ClusterEvent(db.Model, ModelMixin):
    __tablename__ = 'lab_cluster_event'
    __mapper_args__ = {
        'polymorphic_on': 'type',
    }

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Enum(ClusterEventType))
    date = db.Column(db.DateTime(timezone=True))
    user_id = db.Column(postgresql.UUID, nullable=True)
    cluster_id = db.Column(db.Integer, db.ForeignKey('lab_cluster.id'),
                           nullable=False)

    #: :type: :class:`Cluster`
    cluster = db.relationship('Cluster', back_populates='events')

    def to_dict(self):
        data = {}
        for column in self.__table__.columns:
            if hasattr(self, column.name):
                data[column.name] = getattr(self, column.name)
        return data


class ClusterTowerJobEvent(ClusterEvent):
    __mapper_args__ = {
        'polymorphic_identity': ClusterEventType.TOWER_JOB,
    }

    tower_id = db.Column(db.Integer, db.ForeignKey('lab_tower.id'), nullable=False)
    #: ID of template in Tower.
    tower_job_id = db.Column(db.Integer, nullable=False)
    #: :type: :class:`ClusterStatus`
    status = db.Column(db.Enum(ClusterStatus))
    #: :type: :class:`Tower`
    tower = db.relationship('Tower')

    def to_dict(self):
        data = super().to_dict()
        data['status'] = self.status.value
        return data

    def get_tower_job_output(self, output_format='txt'):
        """
        Create Tower client and get job stdout via API.

        See :meth:`rhub.tower.client.Tower.template_job_stdout()`.
        """
        tower_client = self.tower.create_tower_client()
        return tower_client.template_job_stdout(self.tower_job_id, output_format='txt')


class ClusterReservationChangeEvent(ClusterEvent):
    __mapper_args__ = {
        'polymorphic_identity': ClusterEventType.RESERVATION_CHANGE,
    }

    old_value = db.Column(db.DateTime(timezone=True), nullable=True)
    new_value = db.Column(db.DateTime(timezone=True), nullable=True)


class ClusterLifespanChangeEvent(ClusterEvent):
    __mapper_args__ = {
        'polymorphic_identity': ClusterEventType.LIFESPAN_CHANGE,
    }


class ClusterHost(db.Model, ModelMixin):
    __tablename__ = 'lab_cluster_host'

    id = db.Column(db.Integer, primary_key=True)
    cluster_id = db.Column(db.Integer, db.ForeignKey('lab_cluster.id'),
                           nullable=False)
    fqdn = db.Column(db.String(256), nullable=False)
    ipaddr = db.Column(db.ARRAY(postgresql.INET))

    #: :type: :class:`Cluster`
    cluster = db.relationship('Cluster', back_populates='hosts')
