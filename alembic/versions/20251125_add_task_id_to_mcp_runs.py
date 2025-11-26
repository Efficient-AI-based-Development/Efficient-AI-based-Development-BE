"""add task_id to mcp_runs

Revision ID: 20251125_add_task_id
Revises: 20251117
Create Date: 2025-11-25 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20251125_add_task_id_to_mcp_runs"
down_revision: Union[str, None] = "20251117"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # MCPRun 테이블에 task_id 컬럼 추가
    op.add_column(
        "mcp_runs",
        sa.Column(
            "task_id",
            sa.Integer(),
            nullable=True,
            comment="관련 태스크 ID (Start Development 플로우용)",
        ),
    )
    # 외래키 제약조건 추가
    op.create_foreign_key(
        "fk_mcp_runs_task_id",
        "mcp_runs",
        "tasks",
        ["task_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    # 외래키 제약조건 제거
    op.drop_constraint("fk_mcp_runs_task_id", "mcp_runs", type_="foreignkey")
    # task_id 컬럼 제거
    op.drop_column("mcp_runs", "task_id")

