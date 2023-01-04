"""
token api

Revision ID: 30b0f0230558
Revises: 0b6ec8acb058
Create Date: 2023-01-03 12:32:42.245886
"""

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '30b0f0230558'
down_revision = '0b6ec8acb058'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('auth_token', sa.Column('name', sa.String(length=256), nullable=True))


def downgrade():
    op.drop_column('auth_token', 'name')
