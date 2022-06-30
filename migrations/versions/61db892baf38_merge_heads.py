"""
Merge migrations branches.

Revision ID: 61db892baf38
Revises: 01129c0eee22, c98ee40b7a78
Create Date: 2022-06-30 16:16:36.841961
"""

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '61db892baf38'
down_revision = ('01129c0eee22', 'c98ee40b7a78')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
