"""Align MCP session columns with new schema expectations.

Revision ID: 20251109_mcp_session_context
Revises: 20251109_mcp_session_timestamps
Create Date: 2025-11-09
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20251109_mcp_session_context"
down_revision = "20251109_mcp_session_timestamps"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        DECLARE
            v_cnt INTEGER;
        BEGIN
            SELECT COUNT(*)
              INTO v_cnt
              FROM user_tab_cols
             WHERE table_name = 'MCP_SESSIONS'
               AND column_name = 'CONTEXT';

            IF v_cnt = 0 THEN
                EXECUTE IMMEDIATE '
                    ALTER TABLE mcp_sessions
                    ADD (context CLOB)
                ';
            END IF;
        END;
        """
    )


def downgrade():
    op.execute(
        """
        DECLARE
            v_cnt INTEGER;
        BEGIN
            SELECT COUNT(*)
              INTO v_cnt
              FROM user_tab_cols
             WHERE table_name = 'MCP_SESSIONS'
               AND column_name = 'CONTEXT';

            IF v_cnt = 1 THEN
                EXECUTE IMMEDIATE '
                    ALTER TABLE mcp_sessions
                    DROP COLUMN context
                ';
            END IF;
        END;
        """
    )

