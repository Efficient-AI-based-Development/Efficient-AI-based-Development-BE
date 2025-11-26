"""merge heads
Revision ID: 20251117
Revises: 20251109_mcp_run_timestamps, add_task_fields
Create Date: 2025-11-17 15:48:56.050506

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251117'
down_revision = ('20251109_mcp_run_timestamps', '20251109_add_task_fields')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

