# flake8: noqa
"""
lab rework

Revision ID: d17e28bbb0c3
Revises: d0264f75ac84
Create Date: 2022-06-14 13:32:52.784908
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'd17e28bbb0c3'
down_revision = 'd0264f75ac84'
branch_labels = None
depends_on = None


def data_migration():
    count = op.get_bind().execute("SELECT COUNT(id) FROM lab_region").first()[0]
    if count > 0:
        raise NotImplementedError(
            "Data migration is not supported for this migration, delete all data "
            "in the table `lab_region` and `lab_cluster`."
        )


def upgrade():
    data_migration()

    op.add_column('lab_region', sa.Column('openstack_id', sa.Integer(), nullable=False))
    op.create_foreign_key('ix_openstack_cloud', 'lab_region', 'openstack_cloud', ['openstack_id'], ['id'])

    op.add_column('lab_cluster', sa.Column('project_id', sa.Integer(), nullable=False))
    op.create_foreign_key('ix_openstack_project', 'lab_cluster', 'openstack_project', ['project_id'], ['id'])

    op.drop_column('lab_region', 'dns_server_hostname')
    op.drop_column('lab_region', 'dns_server_key')
    op.drop_column('lab_region', 'dns_server_zone')
    op.drop_column('lab_region', 'openstack_credentials')
    op.drop_column('lab_region', 'openstack_domain_id')
    op.drop_column('lab_region', 'openstack_domain_name')
    op.drop_column('lab_region', 'openstack_networks')
    op.drop_column('lab_region', 'openstack_project')
    op.drop_column('lab_region', 'openstack_url')
    op.drop_column('lab_region', 'openstack_keyname')
    op.drop_column('lab_region', 'satellite_credentials')
    op.drop_column('lab_region', 'satellite_hostname')
    op.drop_column('lab_region', 'satellite_insecure')
    op.drop_column('lab_region', 'vault_server')
    op.drop_column('lab_region', 'download_server')

    op.alter_column('lab_region', 'owner_group', new_column_name='owner_group_id')
    op.alter_column('lab_region', 'users_group', new_column_name='users_group_id')


def downgrade():
    data_migration()

    op.alter_column('lab_region', 'owner_group_id', new_column_name='owner_group')
    op.alter_column('lab_region', 'users_group_id', new_column_name='users_group')

    op.add_column('lab_region', sa.Column('dns_server_hostname', sa.VARCHAR(length=256), autoincrement=False, nullable=False))
    op.add_column('lab_region', sa.Column('dns_server_key', sa.VARCHAR(length=256), autoincrement=False, nullable=False))
    op.add_column('lab_region', sa.Column('dns_server_zone', sa.VARCHAR(length=256), autoincrement=False, nullable=False))
    op.add_column('lab_region', sa.Column('openstack_credentials', sa.VARCHAR(length=256), autoincrement=False, nullable=False))
    op.add_column('lab_region', sa.Column('openstack_domain_id', sa.VARCHAR(length=64), autoincrement=False, nullable=False))
    op.add_column('lab_region', sa.Column('openstack_domain_name', sa.VARCHAR(length=64), autoincrement=False, nullable=False))
    op.add_column('lab_region', sa.Column('openstack_networks', postgresql.ARRAY(sa.VARCHAR(length=64)), autoincrement=False, nullable=False))
    op.add_column('lab_region', sa.Column('openstack_project', sa.VARCHAR(length=64), autoincrement=False, nullable=False))
    op.add_column('lab_region', sa.Column('openstack_url', sa.VARCHAR(length=256), autoincrement=False, nullable=False))
    op.add_column('lab_region', sa.Column('openstack_keyname', sa.VARCHAR(length=64), autoincrement=False, nullable=False))
    op.add_column('lab_region', sa.Column('satellite_credentials', sa.VARCHAR(length=256), autoincrement=False, nullable=False))
    op.add_column('lab_region', sa.Column('satellite_hostname', sa.VARCHAR(length=256), autoincrement=False, nullable=False))
    op.add_column('lab_region', sa.Column('satellite_insecure', sa.BOOLEAN(), autoincrement=False, nullable=False))
    op.add_column('lab_region', sa.Column('vault_server', sa.VARCHAR(length=256), autoincrement=False, nullable=False))
    op.add_column('lab_region', sa.Column('download_server', sa.VARCHAR(length=256), autoincrement=False, nullable=False))

    op.drop_constraint('ix_openstack_cloud', 'lab_region', type_='foreignkey')
    op.drop_column('lab_region', 'openstack_id')

    op.drop_constraint('ix_openstack_project', 'lab_cluster', type_='foreignkey')
    op.drop_column('lab_cluster', 'project_id')
