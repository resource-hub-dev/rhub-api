"""
auth

Revision ID: 8558ca0c7f16
Revises: 143432ee0675
Create Date: 2022-11-15 13:31:52.495417
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '8558ca0c7f16'
down_revision = '143432ee0675'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'auth_group',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_table(
        'auth_user',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('external_uuid', postgresql.UUID(), nullable=True),
        sa.Column('name', sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_table(
        'auth_user_group',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['group_id'], ['auth_group.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['auth_user.id'], ),
        sa.PrimaryKeyConstraint('user_id', 'group_id')
    )
    op.create_table(
        'auth_token',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['auth_user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_token_token'), 'auth_token', ['token'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_token_token'), table_name='auth_token')
    op.drop_table('auth_token')
    op.drop_table('auth_user_group')
    op.drop_table('auth_user')
    op.drop_table('auth_group')
