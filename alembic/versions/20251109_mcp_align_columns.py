"""Align MCP connection column names with latest domain model.

Revision ID: 20251109_mcp_align_columns
Revises: 20251109_mcp_add_updated_at
Create Date: 2025-11-09
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20251109_mcp_align_columns"
down_revision = "20251109_mcp_add_updated_at"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        DECLARE
            l_connection_count INTEGER;
            l_provider_count INTEGER;
        BEGIN
            SELECT COUNT(*)
              INTO l_connection_count
              FROM user_tab_cols
             WHERE table_name = 'MCP_CONNECTIONS'
               AND column_name = 'CONNECTION_TYPE';

            IF l_connection_count = 0 THEN
                SELECT COUNT(*)
                  INTO l_provider_count
                  FROM user_tab_cols
                 WHERE table_name = 'MCP_CONNECTIONS'
                   AND column_name = 'PROVIDER_ID';

                IF l_provider_count = 1 THEN
                    EXECUTE IMMEDIATE '
                        ALTER TABLE mcp_connections
                        RENAME COLUMN provider_id TO connection_type
                    ';
                ELSE
                    EXECUTE IMMEDIATE '
                        ALTER TABLE mcp_connections
                        ADD (connection_type VARCHAR2(50))
                    ';
                END IF;
            END IF;
        END;
        """
    )


def downgrade():
    op.execute(
        """
        DECLARE
            l_connection_count INTEGER;
            l_provider_count INTEGER;
        BEGIN
            SELECT COUNT(*)
              INTO l_connection_count
              FROM user_tab_cols
             WHERE table_name = 'MCP_CONNECTIONS'
               AND column_name = 'CONNECTION_TYPE';

            IF l_connection_count = 1 THEN
                SELECT COUNT(*)
                  INTO l_provider_count
                  FROM user_tab_cols
                 WHERE table_name = 'MCP_CONNECTIONS'
                   AND column_name = 'PROVIDER_ID';

                IF l_provider_count = 0 THEN
                    EXECUTE IMMEDIATE '
                        ALTER TABLE mcp_connections
                        RENAME COLUMN connection_type TO provider_id
                    ';
                ELSE
                    EXECUTE IMMEDIATE '
                        ALTER TABLE mcp_connections
                        DROP COLUMN connection_type
                    ';
                END IF;
            END IF;
        END;
        """
    )

