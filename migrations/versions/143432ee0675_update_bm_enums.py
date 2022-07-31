"""
Update BM enums

Revision ID: 143432ee0675
Revises: 21d552549713
Create Date: 2022-07-28 08:49:31.889048
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = '143432ee0675'
down_revision = '21d552549713'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TYPE baremetalboottype RENAME VALUE 'SECURE_BOOT' TO 'UEFI_SECURE_BOOT'")
    op.execute("ALTER TYPE imagebaseos RENAME VALUE 'RED_HAT' TO 'RHEL'")
    op.alter_column('bare_metal_host', 'secure_boot', new_column_name='uefi_secure_boot')
    op.alter_column('bare_metal_image', 'secure_boot', new_column_name='uefi_secure_boot')


def downgrade():
    op.execute("ALTER TYPE baremetalboottype RENAME VALUE 'UEFI_SECURE_BOOT' TO 'SECURE_BOOT'")
    op.execute("ALTER TYPE imagebaseos RENAME VALUE 'RHEL' TO 'RED_HAT'")
    op.alter_column('bare_metal_host', 'uefi_secure_boot', new_column_name='secure_boot')
    op.alter_column('bare_metal_image', 'uefi_secure_boot', new_column_name='secure_boot')
