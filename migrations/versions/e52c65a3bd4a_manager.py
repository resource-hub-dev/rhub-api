"""
manager

Revision ID: e52c65a3bd4a
Revises: 30b0f0230558
Create Date: 2023-01-16 13:25:20.730081
"""

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = 'e52c65a3bd4a'
down_revision = '30b0f0230558'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('auth_user', sa.Column('manager_id', sa.Integer(), nullable=True))
    op.add_column('auth_user', sa.Column('deleted', sa.Boolean(), server_default='FALSE', nullable=True))
    op.create_foreign_key(None, 'auth_user', 'auth_user', ['manager_id'], ['id'])


def downgrade():
    op.drop_constraint(None, 'auth_user', type_='foreignkey')
    op.drop_column('auth_user', 'deleted')
    op.drop_column('auth_user', 'manager_id')
