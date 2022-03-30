"""
location

Revision ID: bdb8dc5132dc
Revises: 820fdebe8007
Create Date: 2022-03-29 16:00:32.364000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bdb8dc5132dc'
down_revision = '820fdebe8007'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'lab_location',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=32), nullable=False),
        sa.Column('description', sa.Text, nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    op.execute(
        """
        INSERT INTO lab_location (name, description)
        SELECT DISTINCT location, '' FROM lab_region WHERE location IS NOT NULL
        """
    )
    op.add_column('lab_region', sa.Column('location_id', sa.Integer(), nullable=True))
    op.execute(
        """
        UPDATE lab_region AS r
        SET location_id = l.id
        FROM lab_location AS l
        WHERE r.location = l.name;
        """
    )
    op.create_foreign_key(
        'lab_region_location_id_fkey',
        'lab_region',
        'lab_location',
        ['location_id'],
        ['id'],
    )
    op.drop_index('ix_lab_region_location', table_name='lab_region')
    op.drop_column('lab_region', 'location')


def downgrade():
    op.add_column(
        'lab_region',
        sa.Column('location', sa.VARCHAR(length=32), nullable=True)
    )
    op.drop_constraint('lab_region_location_id_fkey', 'lab_region')
    op.create_index('ix_lab_region_location', 'lab_region', ['location'], unique=False)
    op.execute(
        """
        UPDATE lab_region AS r
        SET location = l.name
        FROM lab_location AS l
        WHERE r.location_id = l.id
        """
    )
    op.drop_column('lab_region', 'location_id')

    op.drop_table('lab_location')
