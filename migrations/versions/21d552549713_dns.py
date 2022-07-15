"""
dns

Revision ID: 21d552549713
Revises: a15bd1b17f77
Create Date: 2022-07-15 14:14:37.719550
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '21d552549713'
down_revision = 'a15bd1b17f77'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'dns_server',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=32), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('owner_group_id', postgresql.UUID(), nullable=False),
        sa.Column('hostname', sa.String(length=256), nullable=False),
        sa.Column('zone', sa.String(length=256), nullable=False),
        sa.Column('credentials', sa.String(length=256), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('hostname', 'zone', name='ix_dns_server_zone'),
        sa.UniqueConstraint('name')
    )
    op.add_column('lab_region', sa.Column('dns_id', sa.Integer(), nullable=True))
    op.create_foreign_key('lab_region_dns_id_fkey', 'lab_region', 'dns_server', ['dns_id'], ['id'])


def downgrade():
    op.drop_constraint('lab_region_dns_id_fkey', 'lab_region', type_='foreignkey')
    op.drop_column('lab_region', 'dns_id')
    op.drop_table('dns_server')
