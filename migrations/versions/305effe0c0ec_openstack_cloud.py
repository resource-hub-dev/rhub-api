"""
openstack cloud

Revision ID: 305effe0c0ec
Revises: bda4b393f3e5
Create Date: 2022-06-07 14:10:48.399152
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '305effe0c0ec'
down_revision = 'bda4b393f3e5'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'openstack_cloud',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=32), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('owner_group_id', postgresql.UUID(), nullable=False),
        sa.Column('url', sa.String(length=256), nullable=False),
        sa.Column('credentials', sa.String(length=256), nullable=False),
        sa.Column('domain_name', sa.String(length=64), nullable=False),
        sa.Column('domain_id', sa.String(length=64), nullable=False),
        sa.Column('networks', sa.ARRAY(sa.String(length=64)), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )


def downgrade():
    op.drop_table('openstack_cloud')
