"""Ensure MCP run table has timestamp columns.

Revision ID: 20251109_mcp_run_timestamps
Revises: 20251109_mcp_run_cleanup
Create Date: 2025-11-09
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20251109_mcp_run_timestamps"
down_revision = "20251109_mcp_run_cleanup"
branch_labels = None
depends_on = None


def upgrade():
    # created_at 보강
    op.execute(
        """
        DECLARE
            v_cnt INTEGER;
        BEGIN
            SELECT COUNT(*)
              INTO v_cnt
              FROM user_tab_cols
             WHERE table_name = 'MCP_RUNS'
               AND column_name = 'CREATED_AT';

            IF v_cnt = 0 THEN
                EXECUTE IMMEDIATE '
                    ALTER TABLE mcp_runs
                    ADD (created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP)
                ';
            END IF;

            BEGIN
                EXECUTE IMMEDIATE '
                    UPDATE mcp_runs
                       SET created_at = NVL(created_at, SYSTIMESTAMP)
                ';
            EXCEPTION
                WHEN OTHERS THEN
                    NULL;
            END;

            BEGIN
                EXECUTE IMMEDIATE '
                    ALTER TABLE mcp_runs
                    MODIFY (created_at NOT NULL)
                ';
            EXCEPTION
                WHEN OTHERS THEN
                    NULL;
            END;
        END;
        """
    )

    # updated_at 보강
    op.execute(
        """
        DECLARE
            v_cnt INTEGER;
        BEGIN
            SELECT COUNT(*)
              INTO v_cnt
              FROM user_tab_cols
             WHERE table_name = 'MCP_RUNS'
               AND column_name = 'UPDATED_AT';

            IF v_cnt = 0 THEN
                EXECUTE IMMEDIATE '
                    ALTER TABLE mcp_runs
                    ADD (updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP)
                ';
            END IF;

            BEGIN
                EXECUTE IMMEDIATE '
                    UPDATE mcp_runs
                       SET updated_at = NVL(updated_at, created_at)
                ';
            EXCEPTION
                WHEN OTHERS THEN
                    NULL;
            END;

            BEGIN
                EXECUTE IMMEDIATE '
                    ALTER TABLE mcp_runs
                    MODIFY (updated_at NOT NULL)
                ';
            EXCEPTION
                WHEN OTHERS THEN
                    NULL;
            END;
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
             WHERE table_name = 'MCP_RUNS'
               AND column_name = 'UPDATED_AT';

            IF v_cnt = 1 THEN
                EXECUTE IMMEDIATE '
                    ALTER TABLE mcp_runs
                    DROP COLUMN updated_at
                ';
            END IF;

            SELECT COUNT(*)
              INTO v_cnt
              FROM user_tab_cols
             WHERE table_name = 'MCP_RUNS'
               AND column_name = 'CREATED_AT';

            IF v_cnt = 1 THEN
                EXECUTE IMMEDIATE '
                    ALTER TABLE mcp_runs
                    DROP COLUMN created_at
                ';
            END IF;
        END;
        """
    )

