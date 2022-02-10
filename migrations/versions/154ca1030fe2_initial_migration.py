"""
initial migration

Revision ID: 154ca1030fe2
Revises:
Create Date: 2022-02-09 13:24:33.525762
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '154ca1030fe2'
down_revision = None
branch_labels = None
depends_on = None


clusterstatus_enum = sa.Enum(
    'ACTIVE',
    'DELETED',
    'DELETING',
    'DELETION_FAILED',
    'DELETION_QUEUED',
    'INSTALLATION_FAILED',
    'INSTALLATION_QUEUED',
    'INSTALLING',
    'POST_DELETING',
    'POST_DELETION_FAILED',
    'POST_DELETION_QUEUED',
    'POST_INSTALLATION_FAILED',
    'POST_INSTALLATION_QUEUED',
    'POST_INSTALLING',
    'POST_PROVISIONING',
    'POST_PROVISIONING_FAILED',
    'POST_PROVISIONING_QUEUED',
    'PRE_DELETING',
    'PRE_DELETION_FAILED',
    'PRE_DELETION_QUEUED',
    'PRE_INSTALLATION_FAILED',
    'PRE_INSTALLATION_QUEUED',
    'PRE_INSTALLING',
    'PRE_PROVISIONING',
    'PRE_PROVISIONING_FAILED',
    'PRE_PROVISIONING_QUEUED',
    'PROVISIONING',
    'PROVISIONING_FAILED',
    'PROVISIONING_QUEUED',
    'QUEUED',
    name='clusterstatus'
)

clustereventtype_enum = sa.Enum(
    'TOWER_JOB',
    'STATUS_CHANGE',
    'RESERVATION_CHANGE',
    'LIFESPAN_CHANGE',
    name='clustereventtype'
)


def upgrade():
    op.create_table(
        'lab_product',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=True),
        sa.Column('tower_template_name_create', sa.String(length=128), nullable=False),
        sa.Column('tower_template_name_delete', sa.String(length=128), nullable=False),
        sa.Column('parameters', sa.JSON(), nullable=False),
        sa.Column('flavors', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_table(
        'lab_quota',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('num_vcpus', sa.Integer(), nullable=True),
        sa.Column('ram_mb', sa.Integer(), nullable=True),
        sa.Column('num_volumes', sa.Integer(), nullable=True),
        sa.Column('volumes_gb', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'policies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=256), nullable=False),
        sa.Column('department', sa.Text(), nullable=False),
        sa.Column('constraint_sched_avail', sa.ARRAY(sa.Text()), nullable=True),
        sa.Column('constraint_serv_avail', sa.Numeric(), nullable=True),
        sa.Column('constraint_limit', sa.JSON(), nullable=True),
        sa.Column('constraint_density', sa.Text(), nullable=True),
        sa.Column('constraint_tag', sa.ARRAY(sa.Text()), nullable=True),
        sa.Column('constraint_cost', sa.Numeric(), nullable=True),
        sa.Column('constraint_location', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'scheduler_cron',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=True),
        sa.Column('time_expr', sa.String(length=128), nullable=False),
        sa.Column('job_name', sa.Text(), nullable=False),
        sa.Column('job_params', sa.JSON(), nullable=True),
        sa.Column('last_run', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_table(
        'tower_server',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=32), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=True),
        sa.Column('url', sa.String(length=256), nullable=False),
        sa.Column('verify_ssl', sa.Boolean(), nullable=True),
        sa.Column('credentials', sa.String(length=256), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_table(
        'lab_region',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=32), nullable=False),
        sa.Column('location', sa.String(length=32), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('banner', sa.Text(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=True),
        sa.Column('user_quota_id', sa.Integer(), nullable=True),
        sa.Column('total_quota_id', sa.Integer(), nullable=True),
        sa.Column('lifespan_length', sa.Integer(), nullable=True),
        sa.Column('reservations_enabled', sa.Boolean(), nullable=True),
        sa.Column('reservation_expiration_max', sa.Integer(), nullable=True),
        sa.Column('owner_group', postgresql.UUID(), nullable=False),
        sa.Column('users_group', postgresql.UUID(), nullable=True),
        sa.Column('tower_id', sa.Integer(), nullable=True),
        sa.Column('openstack_url', sa.String(length=256), nullable=False),
        sa.Column('openstack_credentials', sa.String(length=256), nullable=False),
        sa.Column('openstack_project', sa.String(length=64), nullable=False),
        sa.Column('openstack_domain_name', sa.String(length=64), nullable=False),
        sa.Column('openstack_domain_id', sa.String(length=64), nullable=False),
        sa.Column('openstack_networks', sa.ARRAY(sa.String(length=64)), nullable=False),
        sa.Column('openstack_keyname', sa.String(length=64), nullable=False),
        sa.Column('satellite_hostname', sa.String(length=256), nullable=False),
        sa.Column('satellite_insecure', sa.Boolean(), nullable=False),
        sa.Column('satellite_credentials', sa.String(length=256), nullable=False),
        sa.Column('dns_server_hostname', sa.String(length=256), nullable=False),
        sa.Column('dns_server_zone', sa.String(length=256), nullable=False),
        sa.Column('dns_server_key', sa.String(length=256), nullable=False),
        sa.Column('vault_server', sa.String(length=256), nullable=False),
        sa.Column('download_server', sa.String(length=256), nullable=False),
        sa.ForeignKeyConstraint(['total_quota_id'], ['lab_quota.id']),
        sa.ForeignKeyConstraint(['tower_id'], ['tower_server.id']),
        sa.ForeignKeyConstraint(['user_quota_id'], ['lab_quota.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(
        op.f('ix_lab_region_location'),
        'lab_region',
        ['location'],
        unique=False
    )
    op.create_index(
        op.f('ix_lab_region_users_group'),
        'lab_region',
        ['users_group'],
        unique=False
    )
    op.create_table(
        'tower_template',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=256), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('server_id', sa.Integer(), nullable=False),
        sa.Column('tower_template_id', sa.Integer(), nullable=False),
        sa.Column('tower_template_is_workflow', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['server_id'], ['tower_server.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_table(
        'lab_cluster',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=32), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('user_id', postgresql.UUID(), nullable=False),
        sa.Column('group_id', postgresql.UUID(), nullable=True),
        sa.Column('created', sa.DateTime(timezone=True), nullable=True),
        sa.Column('region_id', sa.Integer(), nullable=False),
        sa.Column('reservation_expiration', sa.DateTime(timezone=True), nullable=True),
        sa.Column('lifespan_expiration', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', clusterstatus_enum, nullable=True),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('product_params', sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['lab_product.id']),
        sa.ForeignKeyConstraint(['region_id'], ['lab_region.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_table(
        'lab_region_product',
        sa.Column('region_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['product_id'], ['lab_product.id']),
        sa.ForeignKeyConstraint(['region_id'], ['lab_region.id']),
        sa.PrimaryKeyConstraint('region_id', 'product_id')
    )
    op.create_table(
        'tower_job',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('tower_job_id', sa.Integer(), nullable=False),
        sa.Column('launched_by', postgresql.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['template_id'], ['tower_template.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        op.f('ix_tower_job_launched_by'),
        'tower_job',
        ['launched_by'],
        unique=False
    )
    op.create_table(
        'lab_cluster_event',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('type', clustereventtype_enum, nullable=True),
        sa.Column('date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('user_id', postgresql.UUID(), nullable=True),
        sa.Column('cluster_id', sa.Integer(), nullable=False),
        sa.Column('tower_id', sa.Integer(), nullable=True),
        sa.Column('tower_job_id', sa.Integer(), nullable=True),
        sa.Column('status', clusterstatus_enum, nullable=True),
        sa.Column('status_old', clusterstatus_enum, nullable=True),
        sa.Column('status_new', clusterstatus_enum, nullable=True),
        sa.Column('expiration_old', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expiration_new', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['cluster_id'], ['lab_cluster.id']),
        sa.ForeignKeyConstraint(['tower_id'], ['tower_server.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'lab_cluster_host',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cluster_id', sa.Integer(), nullable=False),
        sa.Column('fqdn', sa.String(length=256), nullable=False),
        sa.Column('ipaddr', sa.ARRAY(postgresql.INET()), nullable=True),
        sa.Column('num_vcpus', sa.Integer(), nullable=True),
        sa.Column('ram_mb', sa.Integer(), nullable=True),
        sa.Column('num_volumes', sa.Integer(), nullable=True),
        sa.Column('volumes_gb', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['cluster_id'], ['lab_cluster.id']),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('lab_cluster_host')
    op.drop_table('lab_cluster_event')
    op.drop_index(op.f('ix_tower_job_launched_by'), table_name='tower_job')
    op.drop_table('tower_job')
    op.drop_table('lab_region_product')
    op.drop_table('lab_cluster')
    op.drop_table('tower_template')
    op.drop_index(op.f('ix_lab_region_users_group'), table_name='lab_region')
    op.drop_index(op.f('ix_lab_region_location'), table_name='lab_region')
    op.drop_table('lab_region')
    op.drop_table('tower_server')
    op.drop_table('scheduler_cron')
    op.drop_table('policies')
    op.drop_table('lab_quota')
    op.drop_table('lab_product')

    clusterstatus_enum.drop(op.get_bind(), checkfirst=True)
    clustereventtype_enum.drop(op.get_bind(), checkfirst=True)
