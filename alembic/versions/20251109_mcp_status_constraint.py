"""Normalize MCP connection status constraint.

Revision ID: 20251109_mcp_status_constraint
Revises: 20251109_mcp_align_columns
Create Date: 2025-11-09
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20251109_mcp_status_constraint"
down_revision = "20251109_mcp_align_columns"
branch_labels = None
depends_on = None


def _drop_constraint_if_exists(name: str):
    op.execute(
        f"""
        DECLARE
            l_count INTEGER;
        BEGIN
            SELECT COUNT(*)
              INTO l_count
              FROM user_constraints
             WHERE table_name = 'MCP_CONNECTIONS'
               AND constraint_name = '{name}';

            IF l_count > 0 THEN
                EXECUTE IMMEDIATE 'ALTER TABLE mcp_connections DROP CONSTRAINT {name}';
            END IF;
        END;
        """
    )


def upgrade():
    # 기존 데이터 정규화 (연결 상태 텍스트가 legacy 값일 경우 대비)
    op.execute(
        """
        UPDATE mcp_connections
           SET status = CASE
               WHEN status IN ('connected', 'active') THEN 'pending'
               WHEN status IN ('closed') THEN 'inactive'
               ELSE status
           END
        """
    )

    _drop_constraint_if_exists("CK_MCP_CONN_STATUS")
    _drop_constraint_if_exists("CHK_MCP_CONNECTION_STATUS")

    op.execute(
        """
        ALTER TABLE mcp_connections
        ADD CONSTRAINT ck_mcp_conn_status
        CHECK (status IN ('pending','active','inactive','error'))
        """
    )


def downgrade():
    _drop_constraint_if_exists("CK_MCP_CONN_STATUS")
    _drop_constraint_if_exists("CHK_MCP_CONNECTION_STATUS")

    op.execute(
        """
        ALTER TABLE mcp_connections
        ADD CONSTRAINT ck_mcp_conn_status
        CHECK (status IN ('connected','closed'))
        """
    )

