"""
os project credentials

Revision ID: 03e16ed62a16
Revises: b524ac60c9c5
Create Date: 2023-04-18 13:17:08.936558
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '03e16ed62a16'
down_revision = 'b524ac60c9c5'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('openstack_cloud', schema=None) as batch_op:
        batch_op.alter_column('credentials',
               existing_type=sa.VARCHAR(length=256),
               nullable=True)

    with op.batch_alter_table('openstack_project', schema=None) as batch_op:
        batch_op.add_column(sa.Column('credentials', sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table('openstack_project', schema=None) as batch_op:
        batch_op.drop_column('credentials')

    with op.batch_alter_table('openstack_cloud', schema=None) as batch_op:
        batch_op.alter_column('credentials',
               existing_type=sa.VARCHAR(length=256),
               nullable=False)
