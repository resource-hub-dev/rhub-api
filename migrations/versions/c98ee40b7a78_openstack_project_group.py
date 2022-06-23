"""
openstack project group

Revision ID: c98ee40b7a78
Revises: d17e28bbb0c3
Create Date: 2022-06-21 14:45:36.145632
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'c98ee40b7a78'
down_revision = 'd17e28bbb0c3'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('lab_cluster', 'group_id')
    op.drop_column('lab_cluster', 'user_id')
    op.drop_index('ix_lab_region_users_group', table_name='lab_region')
    op.create_index(op.f('ix_lab_region_users_group_id'), 'lab_region', ['users_group_id'], unique=False)
    op.add_column('openstack_project', sa.Column('group_id', postgresql.UUID(), nullable=True))


def downgrade():
    op.drop_column('openstack_project', 'group_id')
    op.drop_index(op.f('ix_lab_region_users_group_id'), table_name='lab_region')
    op.create_index('ix_lab_region_users_group', 'lab_region', ['users_group_id'], unique=False)
    op.add_column('lab_cluster', sa.Column('user_id', postgresql.UUID(), autoincrement=False, nullable=True))
    op.add_column('lab_cluster', sa.Column('group_id', postgresql.UUID(), autoincrement=False, nullable=True))
