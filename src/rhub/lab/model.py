import datetime

from sqlalchemy.dialects import postgresql

from rhub.api import db, get_vault
from rhub.api.utils import row2dict
from rhub.tower.client import Tower


class Region(db.Model):
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

    #: :type: list of :class:`Cluster`
    clusters = db.relationship('Cluster', back_populates='region')

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
            data[column.name] = getattr(self, column.name)

        if self.quota:
            data['quota'] = row2dict(self.quota)
        else:
            data['quota'] = None

        return data


class Quota(db.Model):
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
        data = {}
        for column in self.__table__.columns:
            if column.name == 'id':
                continue
            data[column.name] = getattr(self, column.name)
        return data


class Tower(db.Model):
    __tablename__ = 'lab_tower'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    enabled = db.Column(db.Boolean, default=True)
    url = db.Column(db.String(256), nullable=False)
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


class Cluster(db.Model):
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
        data = row2dict(self)
        data['quota'] = self.quota
        return data
