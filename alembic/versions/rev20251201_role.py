"""add assigned_role to tasks

Revision ID: rev20251201_role
Revises: 20251125_add_task_id_to_mcp_runs
Create Date: 2025-12-01 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "rev20251201_role"
down_revision: Union[str, None] = "20251125_add_task_id_to_mcp_runs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_columns = {col["name"].lower() for col in inspector.get_columns("tasks")}
    if "assigned_role" not in existing_columns:
        op.add_column(
            "tasks",
            sa.Column(
                "assigned_role",
                sa.String(length=50),
                nullable=True,
                comment="담당 역할 (Backend/Frontend)",
            ),
        )

    existing_checks = {chk["name"].lower() for chk in inspector.get_check_constraints("tasks")}
    if "chk_task_assigned_role" not in existing_checks:
        op.create_check_constraint(
            "chk_task_assigned_role",
            "tasks",
            "(assigned_role IN ('Backend', 'Frontend')) OR assigned_role IS NULL",
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    existing_checks = {chk["name"].lower() for chk in inspector.get_check_constraints("tasks")}
    if "chk_task_assigned_role" in existing_checks:
        op.drop_constraint("chk_task_assigned_role", "tasks", type_="check")

    existing_columns = {col["name"].lower() for col in inspector.get_columns("tasks")}
    if "assigned_role" in existing_columns:
        op.drop_column("tasks", "assigned_role")
