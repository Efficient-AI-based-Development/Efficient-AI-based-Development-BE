"""Cleanup MCP session schema to match domain model.

Revision ID: 20251109_mcp_session_cleanup
Revises: 20251109_mcp_session_context
Create Date: 2025-11-09
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20251109_mcp_session_cleanup"
down_revision = "20251109_mcp_session_context"
branch_labels = None
depends_on = None


def _drop_index_if_exists(name: str):
    op.execute(
        f"""
        DECLARE
            v_cnt INTEGER;
        BEGIN
            SELECT COUNT(*)
              INTO v_cnt
              FROM user_indexes
             WHERE index_name = '{name}';

            IF v_cnt > 0 THEN
                EXECUTE IMMEDIATE 'DROP INDEX {name}';
            END IF;
        END;
        """
    )


def _drop_constraint_if_exists(name: str):
    op.execute(
        f"""
        DECLARE
            v_cnt INTEGER;
        BEGIN
            SELECT COUNT(*)
              INTO v_cnt
              FROM user_constraints
             WHERE constraint_name = '{name}';

            IF v_cnt > 0 THEN
                EXECUTE IMMEDIATE 'ALTER TABLE mcp_sessions DROP CONSTRAINT {name}';
            END IF;
        END;
        """
    )


def upgrade():
    # 기존 자료에서 project_id 값은 연결 테이블과 동일하므로 삭제 전 백업 필요시 고려
    _drop_constraint_if_exists("FK_MCP_SESS_PROJECT")
    _drop_index_if_exists("IX_MCP_SESS_PROJECT")

    op.execute("ALTER TABLE mcp_sessions DROP COLUMN project_id")

    _drop_constraint_if_exists("CK_MCP_SESS_STATUS")
    _drop_constraint_if_exists("CHK_MCP_SESSION_STATUS")
    op.execute(
        """
        ALTER TABLE mcp_sessions
        ADD CONSTRAINT chk_mcp_session_status
        CHECK (status IN ('ready','active','closed','error'))
        """
    )


def downgrade():
    # 복원 시 project_id 컬럼을 다시 추가 (NULL 허용)
    op.execute(
        """
        ALTER TABLE mcp_sessions
        ADD (project_id NUMBER NULL)
        """
    )

    _drop_constraint_if_exists("CHK_MCP_SESSION_STATUS")
    op.execute(
        """
        ALTER TABLE mcp_sessions
        ADD CONSTRAINT ck_mcp_sess_status
        CHECK (status IN ('ready','closed'))
        """
    )

