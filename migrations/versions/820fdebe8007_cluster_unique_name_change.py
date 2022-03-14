"""
cluster unique name change

Revision ID: 820fdebe8007
Revises: 154ca1030fe2
Create Date: 2022-03-14 12:15:09.862003
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '820fdebe8007'
down_revision = '154ca1030fe2'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint('lab_cluster_name_key', 'lab_cluster', type_='unique')
    op.create_index('ix_name', 'lab_cluster', ['name'], unique=True,
                    postgresql_where=sa.text("status != 'DELETED'"))


def downgrade():
    op.drop_index('ix_name', table_name='lab_cluster',
                  postgresql_where=sa.text("status != 'DELETED'"))
    op.create_unique_constraint('lab_cluster_name_key', 'lab_cluster', ['name'])
