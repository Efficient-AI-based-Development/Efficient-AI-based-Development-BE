"""add task fields

Revision ID: add_task_fields
Revises: e6945cbd3c1d
Create Date: 2025-11-13 14:45:08.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20251109_add_task_fields"
down_revision = "20251109_mcp_run_timestamps"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # tasks 테이블에 새 필드 추가
    op.add_column(
        "tasks",
        sa.Column(
            "description_md", sa.CLOB(), nullable=True, comment="태스크 설명 마크다운 (CLOB)"
        ),
    )
    op.add_column(
        "tasks",
        sa.Column(
            "type",
            sa.String(length=50),
            nullable=False,
            server_default=sa.text("'feat'"),
            comment="태스크 타입",
        ),
    )
    op.add_column(
        "tasks",
        sa.Column(
            "source",
            sa.String(length=50),
            nullable=False,
            server_default=sa.text("'USER'"),
            comment="태스크 생성 소스",
        ),
    )
    op.add_column(
        "tasks", sa.Column("tags", sa.CLOB(), nullable=True, comment="태그 목록 (JSON 배열 문자열)")
    )
    op.add_column(
        "tasks", sa.Column("due_at", sa.DateTime(timezone=True), nullable=True, comment="마감일")
    )
    op.add_column(
        "tasks",
        sa.Column(
            "result_files",
            sa.CLOB(),
            nullable=True,
            comment="생성/수정된 파일 목록 (JSON 배열 문자열)",
        ),
    )
    op.add_column("tasks", sa.Column("summary", sa.CLOB(), nullable=True, comment="작업 요약"))
    op.add_column(
        "tasks",
        sa.Column("duration", sa.Integer(), nullable=True, comment="작업 소요 시간 (초 단위)"),
    )
    op.add_column(
        "tasks",
        sa.Column("result_logs", sa.CLOB(), nullable=True, comment="결과 로그 (마크다운 형식)"),
    )

    # status 기본값 변경 및 CHECK 제약조건 업데이트
    op.alter_column(
        "tasks",
        "status",
        existing_type=sa.String(length=50),
        server_default=sa.text("'todo'"),
        comment="태스크 상태",
        existing_nullable=False,
    )

    # priority를 Integer로 변경
    op.alter_column(
        "tasks",
        "priority",
        existing_type=sa.String(length=50),
        type_=sa.Integer(),
        server_default=sa.text("5"),
        comment="우선순위 (0-10)",
        existing_nullable=False,
    )

    # 기존 CHECK 제약조건 삭제
    op.drop_constraint("chk_task_status", "tasks", type_="check")
    op.drop_constraint("chk_task_priority", "tasks", type_="check")

    # 새로운 CHECK 제약조건 추가
    op.create_check_constraint(
        "chk_task_status", "tasks", "status IN ('todo', 'in_progress', 'review', 'done')"
    )
    op.create_check_constraint(
        "chk_task_type", "tasks", "type IN ('feat', 'bug', 'docs', 'design', 'refactor')"
    )
    op.create_check_constraint("chk_task_source", "tasks", "source IN ('MCP', 'USER', 'AI')")
    op.create_check_constraint("chk_task_priority", "tasks", "priority >= 0 AND priority <= 10")


def downgrade() -> None:
    # CHECK 제약조건 삭제
    op.drop_constraint("chk_task_priority", "tasks", type_="check")
    op.drop_constraint("chk_task_source", "tasks", type_="check")
    op.drop_constraint("chk_task_type", "tasks", type_="check")
    op.drop_constraint("chk_task_status", "tasks", type_="check")

    # priority를 String으로 되돌리기
    op.alter_column(
        "tasks",
        "priority",
        existing_type=sa.Integer(),
        type_=sa.String(length=50),
        server_default=sa.text("'medium'"),
        comment="우선순위",
        existing_nullable=False,
    )

    # status 기본값 되돌리기
    op.alter_column(
        "tasks",
        "status",
        existing_type=sa.String(length=50),
        server_default=sa.text("'pending'"),
        comment="태스크 상태",
        existing_nullable=False,
    )

    # 기존 CHECK 제약조건 복원
    op.create_check_constraint(
        "chk_task_status", "tasks", "status IN ('pending', 'in_progress', 'completed', 'blocked')"
    )
    op.create_check_constraint(
        "chk_task_priority", "tasks", "priority IN ('low', 'medium', 'high', 'urgent')"
    )

    # 추가한 컬럼 삭제
    op.drop_column("tasks", "result_logs")
    op.drop_column("tasks", "duration")
    op.drop_column("tasks", "summary")
    op.drop_column("tasks", "result_files")
    op.drop_column("tasks", "due_at")
    op.drop_column("tasks", "tags")
    op.drop_column("tasks", "source")
    op.drop_column("tasks", "type")
    op.drop_column("tasks", "description_md")
