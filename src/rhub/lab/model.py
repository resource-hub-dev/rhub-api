import datetime
import copy

from sqlalchemy.dialects import postgresql

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

    def create_cluster(self, **kwargs):
        """
        A factory to create :class:`Cluster` with
        :attr:`Cluster.lifespan_expiration` set according to
        :attr:`Region.lifespan_length` and current time.
        """
        cluster = Cluster(**kwargs)

        lifespan_delta = datetime.timedelta(days=self.lifespan_length)
        cluster.lifespan_expiration = cluster.created + lifespan_delta

        return cluster

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


class Cluster(db.Model, ModelMixin):
    __tablename__ = 'lab_cluster'

    id = db.Column(db.Integer, primary_key=True)
    region_id = db.Column(db.Integer, db.ForeignKey('lab_region.id'),
                          nullable=False)
    #: :type: :class:`Region`
    region = db.relationship('Region', back_populates='clusters')

    created = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    reservation_expiration = db.Column(db.DateTime, nullable=True)
    #: Cluster lifespan expiration (hard-limit), see
    #: :meth:`Region.create_cluster`.
    lifespan_expiration = db.Column(db.DateTime, nullable=True)

    ...  # TODO

    @property
    def quota(self):
        return self.region.quota

    def to_dict(self):
        data = super().to_dict()
        data['quota'] = self.quota.to_dict()
        return data
