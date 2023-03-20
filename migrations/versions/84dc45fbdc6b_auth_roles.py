"""
auth roles

Revision ID: 84dc45fbdc6b
Revises: e52c65a3bd4a
Create Date: 2023-03-16 12:13:45.451456
"""

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '84dc45fbdc6b'
down_revision = 'e52c65a3bd4a'
branch_labels = None
depends_on = None


roles_enum = sa.Enum('ADMIN', 'LAB_CLUSTER_ADMIN', name='role')


def upgrade():
    roles_enum.create(op.get_bind(), checkfirst=True)
    with op.batch_alter_table('auth_group', schema=None) as batch_op:
        batch_op.add_column(sa.Column('roles', sa.ARRAY(roles_enum), nullable=False, server_default='{}'))


def downgrade():
    with op.batch_alter_table('auth_group', schema=None) as batch_op:
        batch_op.drop_column('roles')
    roles_enum.drop(op.get_bind(), checkfirst=True)
