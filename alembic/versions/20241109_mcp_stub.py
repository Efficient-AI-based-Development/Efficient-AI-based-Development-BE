"""Placeholder migration to keep revision history aligned.

Revision ID: 20241109_mcp_status
Revises: e6945cbd3c1d
Create Date: 2024-11-09
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20241109_mcp_status"
down_revision = "e6945cbd3c1d"
branch_labels = None
depends_on = None


def upgrade():
    """No-op migration kept for revision consistency."""
    op.execute("SELECT 1 FROM dual")


def downgrade():
    """Revert the no-op migration."""
    # 실행 시 의미있는 변경사항이 없으므로 아무 작업도 수행하지 않음
    pass

