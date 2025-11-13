"""Ensure MCP connection table has updated_at column.

Revision ID: 20251109_mcp_add_updated_at
Revises: 20251109_mcp_status
Create Date: 2025-11-09
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20251109_mcp_add_updated_at"
down_revision = "20251109_mcp_status"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        DECLARE
            l_count INTEGER;
        BEGIN
            SELECT COUNT(*)
              INTO l_count
              FROM user_tab_cols
             WHERE table_name = 'MCP_CONNECTIONS'
               AND column_name = 'UPDATED_AT';

            IF l_count = 0 THEN
                EXECUTE IMMEDIATE '
                    ALTER TABLE mcp_connections
                    ADD (updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP)
                ';
                EXECUTE IMMEDIATE '
                    UPDATE mcp_connections
                       SET updated_at = NVL(updated_at, SYSTIMESTAMP)
                ';
                EXECUTE IMMEDIATE '
                    ALTER TABLE mcp_connections
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
            l_count INTEGER;
        BEGIN
            SELECT COUNT(*)
              INTO l_count
              FROM user_tab_cols
             WHERE table_name = 'MCP_CONNECTIONS'
               AND column_name = 'UPDATED_AT';

            IF l_count = 1 THEN
                EXECUTE IMMEDIATE '
                    ALTER TABLE mcp_connections
                    DROP COLUMN updated_at
                ';
            END IF;
        END;
        """
    )

