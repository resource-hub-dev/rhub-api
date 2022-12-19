"""
token expiration

Revision ID: 0b6ec8acb058
Revises: 96de8a527c64
Create Date: 2022-12-19 13:25:14.629105
"""

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '0b6ec8acb058'
down_revision = '96de8a527c64'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('auth_token', sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('auth_token', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))


def downgrade():
    op.drop_column('auth_token', 'created_at')
    op.drop_column('auth_token', 'expires_at')
