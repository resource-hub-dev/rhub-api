"""
status failed

Revision ID: bda4b393f3e5
Revises: bdb8dc5132dc
Create Date: 2022-06-02 11:40:17.976381
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = 'bda4b393f3e5'
down_revision = 'bdb8dc5132dc'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TYPE clusterstatus ADD VALUE 'CREATE_FAILED'")
    op.execute("ALTER TYPE clusterstatus ADD VALUE 'DELETE_FAILED'")


def downgrade():
    pass
