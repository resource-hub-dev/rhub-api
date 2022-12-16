"""
ldap groups

Revision ID: 96de8a527c64
Revises: a2a54a8d6b54
Create Date: 2022-12-15 14:26:56.729833
"""

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '96de8a527c64'
down_revision = 'a2a54a8d6b54'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('auth_group', sa.Column('ldap_dn', sa.String(length=256), nullable=True))


def downgrade():
    op.drop_column('auth_group', 'ldap_dn')
