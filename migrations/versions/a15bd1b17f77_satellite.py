"""
satellite

Revision ID: a15bd1b17f77
Revises: 61db892baf38
Create Date: 2022-07-13 10:57:14.977067
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'a15bd1b17f77'
down_revision = '61db892baf38'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'satellite_server',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=32), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('owner_group_id', postgresql.UUID(), nullable=False),
        sa.Column('hostname', sa.String(length=256), nullable=False),
        sa.Column('insecure', sa.Boolean(), nullable=False),
        sa.Column('credentials', sa.String(length=256), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('hostname'),
        sa.UniqueConstraint('name')
    )

    op.add_column('lab_region', sa.Column('satellite_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'lab_region_satellite_id_fkey',
        'lab_region',
        'satellite_server',
        ['satellite_id'],
        ['id'],
    )


def downgrade():
    op.drop_constraint('lab_region_satellite_id_fkey', 'lab_region', type_='foreignkey')
    op.drop_column('lab_region', 'satellite_id')
    op.drop_table('satellite_server')
