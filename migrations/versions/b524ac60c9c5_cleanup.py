"""
cleanup

Revision ID: b524ac60c9c5
Revises: 84dc45fbdc6b
Create Date: 2023-03-31 12:45:49.818750
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'b524ac60c9c5'
down_revision = '84dc45fbdc6b'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table('bare_metal_provision_qcow2')
    op.drop_table('bare_metal_provision_iso')
    op.drop_table('bare_metal_provision')
    op.drop_table('bare_metal_host_redfish')
    op.drop_table('bare_metal_host_drac')
    op.drop_table('bare_metal_host')
    op.drop_table('bare_metal_image_qcow2')
    op.drop_table('bare_metal_image_iso')
    op.drop_table('bare_metal_handler')
    op.drop_table('bare_metal_image')

    created_enum_names = [
        'baremetalarch',
        'baremetalboottype',
        'baremetalhandlerstatus',
        'baremetalhandlertype',
        'baremetalhardwaretype',
        'baremetalhoststatus',
        'baremetalimagetype',
        'baremetalprovisionstatus',
        'baremetalprovisiontype',
        'imagebaseos',
    ]
    for enum_name in created_enum_names:
        sa_enum = sa.Enum(name=enum_name)
        sa_enum.drop(op.get_bind(), checkfirst=True)


def downgrade():
    raise NotImplementedError
