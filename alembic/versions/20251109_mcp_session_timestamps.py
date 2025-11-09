"""Ensure MCP session table has created_at/updated_at columns.

Revision ID: 20251109_mcp_session_timestamps
Revises: 20251109_mcp_status_constraint
Create Date: 2025-11-09
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20251109_mcp_session_timestamps"
down_revision = "20251109_mcp_status_constraint"
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
               AND column_name = 'CREATED_AT';

            IF v_cnt = 0 THEN
                EXECUTE IMMEDIATE '
                    ALTER TABLE mcp_sessions
                    ADD (created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP)
                ';
                EXECUTE IMMEDIATE '
                    UPDATE mcp_sessions
                       SET created_at = NVL(created_at, SYSTIMESTAMP)
                ';
                EXECUTE IMMEDIATE '
                    ALTER TABLE mcp_sessions
                    MODIFY (created_at NOT NULL)
                ';
            END IF;

            SELECT COUNT(*)
              INTO v_cnt
              FROM user_tab_cols
             WHERE table_name = 'MCP_SESSIONS'
               AND column_name = 'UPDATED_AT';

            IF v_cnt = 0 THEN
                EXECUTE IMMEDIATE '
                    ALTER TABLE mcp_sessions
                    ADD (updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP)
                ';
                EXECUTE IMMEDIATE '
                    UPDATE mcp_sessions
                       SET updated_at = NVL(updated_at, SYSTIMESTAMP)
                ';
                EXECUTE IMMEDIATE '
                    ALTER TABLE mcp_sessions
                    MODIFY (updated_at NOT NULL)
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
               AND column_name = 'UPDATED_AT';

            IF v_cnt = 1 THEN
                EXECUTE IMMEDIATE '
                    ALTER TABLE mcp_sessions
                    DROP COLUMN updated_at
                ';
            END IF;

            SELECT COUNT(*)
              INTO v_cnt
              FROM user_tab_cols
             WHERE table_name = 'MCP_SESSIONS'
               AND column_name = 'CREATED_AT';

            IF v_cnt = 1 THEN
                EXECUTE IMMEDIATE '
                    ALTER TABLE mcp_sessions
                    DROP COLUMN created_at
                ';
            END IF;
        END;
        """
    )

