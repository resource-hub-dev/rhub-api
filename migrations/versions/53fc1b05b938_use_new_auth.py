"""
use new auth

Revision ID: acd5894aa166
Revises: 8558ca0c7f16
Create Date: 2022-11-24 13:19:52.067984
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'acd5894aa166'
down_revision = '8558ca0c7f16'
branch_labels = None
depends_on = None


def data_migration():
    tables = ['dns_server', 'lab_cluster_event', 'lab_region', 'openstack_project', 'openstack_cloud']
    for table in tables:
        count = op.get_bind().execute(f'SELECT COUNT(id) FROM {table}').first()[0]
        if count > 0:
            raise NotImplementedError(
                "Data migration is not supported for this migration, delete all data "
                f"in tables {', '.join(tables)}."
            )


def upgrade():
    data_migration()

    op.drop_index('ix_token_token', table_name='auth_token')
    op.create_index(op.f('ix_auth_token_token'), 'auth_token', ['token'], unique=False)

    op.add_column('auth_user', sa.Column('email', sa.String(length=128), nullable=True))

    op.drop_column('dns_server', 'owner_group_id')
    op.add_column('dns_server', sa.Column('owner_group_id', sa.Integer(), nullable=False))
    op.create_foreign_key('fk_owner_group_id', 'dns_server', 'auth_group', ['owner_group_id'], ['id'])

    op.drop_column('lab_cluster_event', 'user_id')
    op.add_column('lab_cluster_event', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_user_id', 'lab_cluster_event', 'auth_user', ['user_id'], ['id'])

    op.drop_index('ix_lab_region_users_group_id', table_name='lab_region')
    op.drop_column('lab_region', 'users_group_id')
    op.add_column('lab_region', sa.Column('users_group_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_users_group_id', 'lab_region', 'auth_group', ['users_group_id'], ['id'])
    op.drop_column('lab_region', 'owner_group_id')
    op.add_column('lab_region', sa.Column('owner_group_id', sa.Integer(), nullable=False))
    op.create_foreign_key('fk_owner_group_id', 'lab_region', 'auth_group', ['owner_group_id'], ['id'])

    op.drop_column('openstack_cloud', 'owner_group_id')
    op.add_column('openstack_cloud', sa.Column('owner_group_id', sa.Integer(), nullable=False))
    op.create_foreign_key('fk_owner_group_id', 'openstack_cloud', 'auth_group', ['owner_group_id'], ['id'])

    op.drop_column('openstack_project', 'group_id')
    op.add_column('openstack_project', sa.Column('group_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_group_id', 'openstack_project', 'auth_group', ['group_id'], ['id'])
    op.drop_column('openstack_project', 'owner_id')
    op.add_column('openstack_project', sa.Column('owner_id', sa.Integer(), nullable=False))
    op.create_foreign_key('fk_owner_id', 'openstack_project', 'auth_user', ['owner_id'], ['id'])

    op.add_column('policies', sa.Column('owner_group_id', sa.Integer(), nullable=False))
    op.create_foreign_key('fk_owner_group_id', 'policies', 'auth_group', ['owner_group_id'], ['id'])

    op.drop_column('satellite_server', 'owner_group_id')
    op.add_column('satellite_server', sa.Column('owner_group_id', sa.Integer(), nullable=False))
    op.create_foreign_key('fk_owner_group_id', 'satellite_server', 'auth_group', ['owner_group_id'], ['id'])

    op.drop_index('ix_tower_job_launched_by', table_name='tower_job')
    op.drop_column('tower_job', 'launched_by')
    op.add_column('tower_job', sa.Column('launched_by', sa.Integer(), nullable=False))
    op.create_foreign_key('fk_launched_by', 'tower_job', 'auth_user', ['launched_by'], ['id'])


def downgrade():
    data_migration()

    op.drop_constraint('fk_launched_by', 'tower_job', type_='foreignkey')
    op.drop_column('tower_job', 'launched_by')
    op.add_column('tower_job', sa.Column('launched_by', postgresql.UUID(), nullable=False))
    op.create_index('ix_tower_job_launched_by', 'tower_job', ['launched_by'], unique=False)

    op.drop_constraint('fk_owner_group_id', 'satellite_server', type_='foreignkey')
    op.drop_column('satellite_server', 'owner_group_id')
    op.add_column('satellite_server', sa.Column('owner_group_id', postgresql.UUID(), nullable=False))

    op.drop_constraint('fk_owner_group_id', 'policies', type_='foreignkey')
    op.drop_column('policies', 'owner_group_id')

    op.drop_constraint('fk_owner_id', 'openstack_project', type_='foreignkey')
    op.drop_column('openstack_project', 'owner_id')
    op.add_column('openstack_project', sa.Column('owner_id', postgresql.UUID(), nullable=False))
    op.drop_constraint('fk_group_id', 'openstack_project', type_='foreignkey')
    op.drop_column('openstack_project', 'group_id')
    op.add_column('openstack_project', sa.Column('group_id', postgresql.UUID(), nullable=True))

    op.drop_constraint('fk_owner_group_id', 'openstack_cloud', type_='foreignkey')
    op.drop_column('openstack_cloud', 'owner_group_id')
    op.add_column('openstack_cloud', sa.Column('owner_group_id', postgresql.UUID(), nullable=False))

    op.drop_constraint('fk_owner_group_id', 'lab_region', type_='foreignkey')
    op.drop_column('lab_region', 'owner_group_id')
    op.add_column('lab_region', sa.Column('owner_group_id', postgresql.UUID(), nullable=False))
    op.drop_constraint('fk_users_group_id', 'lab_region', type_='foreignkey')
    op.drop_column('lab_region', 'users_group_id')
    op.add_column('lab_region', sa.Column('users_group_id', postgresql.UUID(), nullable=True))
    op.create_index('ix_lab_region_users_group_id', 'lab_region', ['users_group_id'], unique=False)

    op.drop_constraint('fk_user_id', 'lab_cluster_event', type_='foreignkey')
    op.drop_column('lab_cluster_event', 'user_id')
    op.add_column('lab_cluster_event', sa.Column('user_id', postgresql.UUID(), nullable=True))

    op.drop_constraint('fk_owner_group_id', 'dns_server', type_='foreignkey')
    op.drop_column('dns_server', 'owner_group_id')
    op.add_column('dns_server', sa.Column('owner_group_id', postgresql.UUID(), nullable=False))

    op.drop_column('auth_user', 'email')

    op.drop_index(op.f('ix_auth_token_token'), table_name='auth_token')
    op.create_index('ix_token_token', 'auth_token', ['token'], unique=False)
