import datetime
import enum
import re

from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import validates

from rhub.api import db, di
from rhub.api.utils import ModelMixin, condition_eval
from rhub.auth.keycloak import KeycloakClient
from rhub.lab import SHAREDCLUSTER_GROUP
from rhub.openstack import model as openstack_model
from rhub.tower import model as tower_model


class Location(db.Model, ModelMixin):
    __tablename__ = 'lab_location'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False, default='')

    regions = db.relationship('Region', back_populates='location')


class Region(db.Model, ModelMixin):
    __tablename__ = 'lab_region'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), unique=True, nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('lab_location.id'))
    location = db.relationship('Location', back_populates='regions')
    description = db.Column(db.Text, nullable=False, default='')
    banner = db.Column(db.Text, nullable=False, default='')
    enabled = db.Column(db.Boolean, default=True)
    user_quota_id = db.Column(db.Integer, db.ForeignKey('lab_quota.id'),
                              nullable=True)
    #: :type: :class:`Quota` resources limit that single user can use, if
    #: exceeded the user should not be able to create new reservations
    user_quota = db.relationship('Quota', uselist=False, foreign_keys=[user_quota_id])
    total_quota_id = db.Column(db.Integer, db.ForeignKey('lab_quota.id'),
                               nullable=True)
    #: :type: :class:`Quota` total region resources limits, if exceeded no user
    #: should be able to create new reservations
    total_quota = db.relationship('Quota', uselist=False, foreign_keys=[total_quota_id])
    lifespan_length = db.Column(db.Integer, nullable=True)
    reservations_enabled = db.Column(db.Boolean, default=True)
    reservation_expiration_max = db.Column(db.Integer, nullable=True)
    owner_group_id = db.Column(postgresql.UUID, nullable=False)
    #: Limits use only to specific group of people. `NULL` == shared lab.
    users_group_id = db.Column(postgresql.UUID, nullable=True, index=True)
    ...  # TODO policies?
    tower_id = db.Column(db.Integer, db.ForeignKey(tower_model.Server.id))
    #: :type: :class:`rhub.tower.model.Server`
    tower = db.relationship(tower_model.Server)

    openstack_id = db.Column(db.Integer, db.ForeignKey('openstack_cloud.id'),
                             nullable=False)
    openstack = db.relationship(openstack_model.Cloud)

    #: :type: list of :class:`Cluster`
    clusters = db.relationship('Cluster', back_populates='region')

    #: :type: list of :class:`RegionProduct`
    products_relation = db.relationship('RegionProduct', back_populates='region',
                                        lazy='dynamic')

    __embedded__ = ['user_quota', 'total_quota']
    __embedded_ro__ = ['location', 'openstack']

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

    @property
    def owner_group_name(self):
        return di.get(KeycloakClient).group_get(self.owner_group_id)['name']

    @property
    def users_group_name(self):
        if self.users_group_id:
            return di.get(KeycloakClient).group_get(self.users_group_id)['name']
        return None

    def to_dict(self):
        data = super().to_dict()

        del data['user_quota_id']
        del data['total_quota_id']

        data['owner_group_name'] = self.owner_group_name
        data['users_group_name'] = self.users_group_name

        return data

    def get_user_quota_usage(self, user_id):
        query = (
            db.session.query(
                db.func.coalesce(db.func.sum(ClusterHost.num_vcpus), 0),
                db.func.coalesce(db.func.sum(ClusterHost.ram_mb), 0),
                db.func.coalesce(db.func.sum(ClusterHost.num_volumes), 0),
                db.func.coalesce(db.func.sum(ClusterHost.volumes_gb), 0),
            )
            .join(
                Cluster,
                ClusterHost.cluster_id == Cluster.id,
            )
            .where(
                db.and_(
                    Cluster.region_id == self.id,
                    Cluster.owner_id == user_id,
                )
            )
        )
        result = query.first()

        return dict(zip(['num_vcpus', 'ram_mb', 'num_volumes', 'volumes_gb'], result))

    def get_total_quota_usage(self):
        query = (
            db.session.query(
                db.func.coalesce(db.func.sum(ClusterHost.num_vcpus), 0),
                db.func.coalesce(db.func.sum(ClusterHost.ram_mb), 0),
                db.func.coalesce(db.func.sum(ClusterHost.num_volumes), 0),
                db.func.coalesce(db.func.sum(ClusterHost.volumes_gb), 0),
            )
            .join(
                Cluster,
                ClusterHost.cluster_id == Cluster.id,
            )
            .where(
                Cluster.region_id == self.id,
            )
        )
        result = query.first()

        return dict(zip(['num_vcpus', 'ram_mb', 'num_volumes', 'volumes_gb'], result))

    def is_product_enabled(self, product_id):
        """Check if the product is configured and enabled in the region."""
        region_product = self.products_relation.filter(
            db.and_(
                RegionProduct.product_id == product_id,
                RegionProduct.enabled.is_(True),
            ),
        ).first()
        return bool(region_product and region_product.product.enabled)


class Quota(db.Model, ModelMixin):
    __tablename__ = 'lab_quota'

    id = db.Column(db.Integer, primary_key=True)
    num_vcpus = db.Column(db.Integer, nullable=True)
    ram_mb = db.Column(db.Integer, nullable=True)
    num_volumes = db.Column(db.Integer, nullable=True)
    volumes_gb = db.Column(db.Integer, nullable=True)

    def to_dict(self):
        data = super().to_dict()
        del data['id']
        return data


class ClusterStatus(str, enum.Enum):
    ACTIVE = 'Active', 'active'
    PRE_PROVISIONING_QUEUED = 'Pre-Provisioning Queued', 'creating'
    PRE_PROVISIONING = 'Pre-Provisioning', 'creating'
    PRE_PROVISIONING_FAILED = 'Pre-Provisioning Failed', 'failed'
    PROVISIONING_QUEUED = 'Provisioning Queued', 'creating'
    PROVISIONING = 'Provisioning', 'creating'
    PROVISIONING_FAILED = 'Provisioning Failed', 'failed'
    POST_PROVISIONING_QUEUED = 'Post-Provisioning Queued', 'creating'
    POST_PROVISIONING = 'Post-Provisioning', 'creating'
    POST_PROVISIONING_FAILED = 'Post-Provisioning Failed', 'failed'
    PRE_INSTALLATION_QUEUED = 'Pre-Installation Queued', 'creating'
    PRE_INSTALLING = 'Pre-Installing', 'creating'
    PRE_INSTALLATION_FAILED = 'Pre-Installation Failed', 'failed'
    INSTALLATION_QUEUED = 'Installation Queued', 'creating'
    INSTALLING = 'Installing', 'creating'
    INSTALLATION_FAILED = 'Installation Failed', 'failed'
    POST_INSTALLATION_QUEUED = 'Post-Installation Queued', 'creating'
    POST_INSTALLING = 'Post-Installing', 'creating'
    POST_INSTALLATION_FAILED = 'Post-Installation Failed', 'failed'
    PRE_DELETION_QUEUED = 'Pre-Deletion Queued', 'deleting'
    PRE_DELETING = 'Pre-Deleting', 'deleting'
    PRE_DELETION_FAILED = 'Pre-Deletion Failed', 'failed'
    DELETION_QUEUED = 'Deletion Queued', 'deleting'
    DELETING = 'Deleting', 'deleting'
    DELETION_FAILED = 'Deletion Failed', 'failed'
    POST_DELETION_QUEUED = 'Post-Deletion Queued', 'deleting'
    POST_DELETING = 'Post-Deleting', 'deleting'
    POST_DELETION_FAILED = 'Post-Deletion Failed', 'failed'
    DELETED = 'Deleted', 'deleted'
    QUEUED = 'Queued', 'creating'
    CREATE_FAILED = 'Create Failed', 'failed'  # Unknown create failure
    DELETE_FAILED = 'Delete Failed', 'failed'  # Unknown delete failure

    def __new__(cls, value, flag=None):
        if not flag:
            raise ValueError(f'Missing flag for status {value}')
        obj = str.__new__(cls, [value])
        obj._value_ = value
        obj.flag = flag
        return obj

    @property
    def is_active(self):
        return self.flag == 'active'

    @property
    def is_deleted(self):
        return self.flag == 'deleted'

    @property
    def is_failed(self):
        return self.flag == 'failed'

    @property
    def is_creating(self):
        return self.flag == 'creating'

    @property
    def is_deleting(self):
        return self.flag == 'deleting'

    @classmethod
    def flag_statuses(cls, flag):
        """Get list of status for a given flag."""
        return [i for i in cls if i.flag == flag]


class Cluster(db.Model, ModelMixin):
    __tablename__ = 'lab_cluster'
    __table_args__ = (
        db.Index(
            'ix_name',
            'name',
            unique=True,
            postgresql_where=(
                db.Column('status') != ClusterStatus.DELETED.name
            ),
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), nullable=False)
    description = db.Column(db.Text, nullable=False, default='')
    created = db.Column(db.DateTime(timezone=True))

    region_id = db.Column(db.Integer, db.ForeignKey('lab_region.id'),
                          nullable=False)
    #: :type: :class:`Region`
    region = db.relationship('Region', back_populates='clusters')

    project_id = db.Column(db.Integer, db.ForeignKey('openstack_project.id'),
                           nullable=False)
    project = db.relationship(openstack_model.Project)

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

    product_id = db.Column(db.Integer, db.ForeignKey('lab_product.id'),
                           nullable=False)
    product_params = db.Column(db.JSON, nullable=False)
    product = db.relationship('Product', back_populates='clusters')

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
        """
        User quota.

        :type: :class:`Quota` or `None`
        """
        if self.region:
            return self.region.user_quota
        return None

    @property
    def quota_usage(self):
        """
        User quota usage.

        :type: dict or `None`
        """
        usage = dict.fromkeys(['num_vcpus', 'ram_mb', 'num_volumes', 'volumes_gb'], 0)
        for host in self.hosts:
            for k in usage:
                usage[k] += getattr(host, k)
        return usage

    @hybrid_property
    def owner_id(self):
        return self.project.owner_id

    @owner_id.expression
    def owner_id(self):
        return openstack_model.Project.owner_id

    @property
    def owner_name(self):
        return self.project.owner_name

    @hybrid_property
    def group_id(self):
        return self.project.group_id

    @group_id.expression
    def group_id(self):
        return openstack_model.Project.group_id

    @property
    def group_name(self):
        return self.project.group_name

    @property
    def shared(self):
        return self.group_name == SHAREDCLUSTER_GROUP

    @property
    def tower_launch_extra_vars(self):
        rhub_extra_vars = {
            'rhub_cluster_id': self.id,
            'rhub_cluster_name': self.name,
            'rhub_product_id': self.product.id,
            'rhub_product_name': self.product.name,
            'rhub_region_id': self.region.id,
            'rhub_region_name': self.region.name,
            'rhub_project_id': self.project.id,
            'rhub_project_name': self.project.name,
            'rhub_user_id': self.owner_id,
            'rhub_user_name': self.owner_name,
        }
        return rhub_extra_vars | self.product_params

    def to_dict(self):
        data = super().to_dict()

        data['region_name'] = self.region.name
        data['owner_id'] = self.owner_id
        data['owner_name'] = self.owner_name
        data['group_id'] = self.group_id
        data['group_name'] = self.group_name
        data['project_id'] = self.project.id
        data['project_name'] = self.project.name
        data['shared'] = self.shared

        if self.hosts:
            data['hosts'] = [host.to_dict() for host in self.hosts]
        else:
            data['hosts'] = []

        if self.quota:
            data['quota'] = self.quota.to_dict()
            data['quota_usage'] = self.quota_usage
        else:
            data['quota'] = None
            data['quota_usage'] = None

        if self.status:
            data['status'] = self.status.value
            data['status_flag'] = self.status.flag
        else:
            data['status'] = None
            data['status_flag'] = None

        data['product_name'] = self.product.name

        return data


class ClusterEventType(str, enum.Enum):
    TOWER_JOB = 'tower_job'
    STATUS_CHANGE = 'status_change'
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

    @property
    def user_name(self):
        if self.user_id:
            return di.get(KeycloakClient).user_get(self.user_id)['username']
        return None

    def to_dict(self):
        data = {}
        for column in self.__table__.columns:
            if hasattr(self, column.name):
                data[column.name] = getattr(self, column.name)

        # These attributes have different column names, see subclasses below.
        for i in ['old_value', 'new_value']:
            if hasattr(self, i):
                data[i] = getattr(self, i)

        data['user_name'] = self.user_name

        return data


class ClusterTowerJobEvent(ClusterEvent):
    __mapper_args__ = {
        'polymorphic_identity': ClusterEventType.TOWER_JOB,
    }

    tower_id = db.Column(db.Integer, db.ForeignKey(tower_model.Server.id),
                         nullable=True)
    #: ID of template in Tower.
    tower_job_id = db.Column(db.Integer, nullable=True)
    #: :type: :class:`ClusterStatus`
    status = db.Column(db.Enum(ClusterStatus))
    #: :type: :class:`rhub.tower.model.Server`
    tower = db.relationship(tower_model.Server)

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


class ClusterStatusChangeEvent(ClusterEvent):
    __mapper_args__ = {
        'polymorphic_identity': ClusterEventType.STATUS_CHANGE,
    }

    old_value = db.Column('status_old', db.Enum(ClusterStatus))
    new_value = db.Column('status_new', db.Enum(ClusterStatus))

    def to_dict(self):
        data = super().to_dict()
        data["new_value"] = self.new_value.value
        data["old_value"] = self.old_value.value
        return data


class ClusterReservationChangeEvent(ClusterEvent):
    __mapper_args__ = {
        'polymorphic_identity': ClusterEventType.RESERVATION_CHANGE,
    }

    old_value = db.Column('expiration_old', db.DateTime(timezone=True), nullable=True)
    new_value = db.Column('expiration_new', db.DateTime(timezone=True), nullable=True)


class ClusterLifespanChangeEvent(ClusterReservationChangeEvent):
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
    num_vcpus = db.Column(db.Integer, nullable=True)
    ram_mb = db.Column(db.Integer, nullable=True)
    num_volumes = db.Column(db.Integer, nullable=True)
    volumes_gb = db.Column(db.Integer, nullable=True)
    #: :type: :class:`Cluster`
    cluster = db.relationship('Cluster', back_populates='hosts')


class Product(db.Model, ModelMixin):
    __tablename__ = 'lab_product'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False, default='')
    enabled = db.Column(db.Boolean, default=True)
    tower_template_name_create = db.Column(db.String(128), nullable=False)
    tower_template_name_delete = db.Column(db.String(128), nullable=False)
    parameters = db.Column(db.JSON, nullable=False)
    flavors = db.Column(db.JSON, nullable=True)

    #: :type: list of :class:`RegionProduct`
    regions_relation = db.relationship('RegionProduct', back_populates='product',
                                       lazy='dynamic')
    #: :type: list of :class:`Cluster`
    clusters = db.relationship('Cluster', back_populates='product')

    @property
    def parameters_variables(self):
        return [param['variable'] for param in self.parameters]

    @property
    def parameters_defaults(self):
        return {
            param['variable']: param['default']
            for param in self.parameters
            if 'default' in param
        }

    def validate_cluster_params(self, cluster_params):
        invalid_params = {}

        if extra_params := set(cluster_params) - set(self.parameters_variables):
            for i in extra_params:
                invalid_params[i] = 'not allowed'

        for param_spec in self.parameters:
            var = param_spec['variable']

            if var not in cluster_params:
                if param_spec['required']:
                    invalid_params[var] = 'is required'
                continue

            t = param_spec['type']

            if t == 'string':
                if not isinstance(cluster_params[var], str):
                    invalid_params[var] = 'must be a string'

                if param_spec.get('maxLength') is not None:
                    max_len = param_spec['maxLength']
                    if len(cluster_params[var]) > max_len:
                        invalid_params[var] = (
                            f'invalid value, maximal length is {max_len}'
                        )
                if param_spec.get('minLength') is not None:
                    min_len = param_spec['minLength']
                    if len(cluster_params[var]) < min_len:
                        invalid_params[var] = (
                            f'invalid vlue, minimal length is {min_len}'
                        )

            elif t == 'integer':
                if type(cluster_params[var]) is not int:
                    invalid_params[var] = 'must be an integer'

                if param_spec.get('max') is not None:
                    max_val = param_spec['max']
                    if cluster_params[var] > max_val:
                        invalid_params[var] = (
                            f'invalid value, maximal value is {max_val}'
                        )
                if param_spec.get('min') is not None:
                    min_val = param_spec['min']
                    if cluster_params[var] < min_val:
                        invalid_params[var] = (
                            f'invalid value, minimal value is {min_val}'
                        )

            elif t == 'boolean':
                if not isinstance(cluster_params[var], bool):
                    invalid_params[var] = 'must be a boolean'

            if (e := param_spec.get('enum')) is not None:
                if cluster_params[var] not in e:
                    invalid_params[var] = 'value not allowed'

            if (c := param_spec.get('condition')) is not None:
                if not condition_eval(c['data'], cluster_params):
                    invalid_params[var] = 'value does not satisfy the condition'

        if invalid_params:
            raise ValueError(invalid_params)


class RegionProduct(db.Model, ModelMixin):
    """Region-Product N-N association table."""
    __tablename__ = 'lab_region_product'

    region_id = db.Column(db.Integer, db.ForeignKey('lab_region.id'),
                          primary_key=True)
    region = db.relationship('Region', back_populates='products_relation')

    product_id = db.Column(db.Integer, db.ForeignKey('lab_product.id'),
                           primary_key=True)
    product = db.relationship('Product', back_populates='regions_relation')

    enabled = db.Column(db.Boolean, default=True)
