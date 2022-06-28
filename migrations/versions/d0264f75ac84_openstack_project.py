"""
openstack project

Revision ID: d0264f75ac84
Revises: 305effe0c0ec
Create Date: 2022-06-09 12:38:16.196417
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'd0264f75ac84'
down_revision = '305effe0c0ec'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'openstack_project',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cloud_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('owner_id', postgresql.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['cloud_id'], ['openstack_cloud.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cloud_id', 'name', name='ix_cloud_project')
    )


def downgrade():
    op.drop_table('openstack_project')
