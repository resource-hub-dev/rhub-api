"""
ldap user

Revision ID: a2a54a8d6b54
Revises: acd5894aa166
Create Date: 2022-12-13 14:02:25.766978
"""

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = 'a2a54a8d6b54'
down_revision = 'acd5894aa166'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('auth_user', sa.Column('ssh_keys', sa.ARRAY(sa.Text()), server_default='{}', nullable=False))
    op.add_column('auth_user', sa.Column('ldap_dn', sa.String(length=256), nullable=True))
    op.add_column('auth_user', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))
    op.add_column('auth_user', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))


def downgrade():
    op.drop_column('auth_user', 'created_at')
    op.drop_column('auth_user', 'updated_at')
    op.drop_column('auth_user', 'ldap_dn')
    op.drop_column('auth_user', 'ssh_keys')
