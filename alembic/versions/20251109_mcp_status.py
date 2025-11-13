"""Update MCP tables for provider-specific metadata.

Revision ID: 20251109_mcp_status
Revises: 20241109_mcp_status
Create Date: 2025-11-09
"""


from alembic import op

# revision identifiers, used by Alembic.
revision = "20251109_mcp_status"
down_revision = "20241109_mcp_status"
branch_labels = None
depends_on = None


def _drop_constraint_if_exists(name: str):
    """Oracle은 IF EXISTS 구문을 지원하지 않으므로 PL/SQL 블록으로 처리."""
    op.execute(
        f"""
        DECLARE
            l_count INTEGER;
        BEGIN
            SELECT COUNT(*)
              INTO l_count
              FROM user_constraints
             WHERE table_name = 'MCP_CONNECTIONS'
               AND constraint_name = UPPER('{name}');

            IF l_count > 0 THEN
                EXECUTE IMMEDIATE 'ALTER TABLE mcp_connections DROP CONSTRAINT {name}';
            END IF;
        END;
        """
    )


def _add_column_if_not_exists(table_name: str, column_name: str, column_type: str):
    """이미 존재하는 컬럼을 중복 추가하지 않도록 Oracle용 방어 로직."""
    uppercase_name = column_name.upper()
    op.execute(
        f"""
        DECLARE
            l_count INTEGER;
        BEGIN
            SELECT COUNT(*)
              INTO l_count
              FROM user_tab_cols
             WHERE table_name = UPPER('{table_name}')
               AND column_name = '{uppercase_name}';

            IF l_count = 0 THEN
                EXECUTE IMMEDIATE 'ALTER TABLE {table_name} ADD "{uppercase_name}" {column_type}';
            END IF;
        END;
        """
    )


def upgrade():
    """Apply MCP status constraint changes and add JSON columns."""
    op.execute("ALTER TABLE mcp_connections MODIFY (status DEFAULT 'pending')")

    _drop_constraint_if_exists("CHK_MCP_CONNECTION_STATUS")
    op.execute(
        """
        ALTER TABLE mcp_connections
        ADD CONSTRAINT chk_mcp_connection_status
        CHECK (status IN ('pending', 'active', 'inactive', 'error'))
        """
    )

    _add_column_if_not_exists("mcp_connections", "config", "CLOB")
    _add_column_if_not_exists("mcp_connections", "env", "CLOB")

    _add_column_if_not_exists("mcp_sessions", "metadata", "CLOB")

    _add_column_if_not_exists("mcp_runs", "mode", "VARCHAR2(50)")
    _add_column_if_not_exists("mcp_runs", "config", "CLOB")


def downgrade():
    """Revert MCP status constraint changes and remove columns."""
    op.execute("ALTER TABLE mcp_connections MODIFY (status DEFAULT 'active')")

    _drop_constraint_if_exists("CHK_MCP_CONNECTION_STATUS")
    op.execute(
        """
        ALTER TABLE mcp_connections
        ADD CONSTRAINT chk_mcp_connection_status
        CHECK (status IN ('active', 'inactive', 'error'))
        """
    )

    op.drop_column("mcp_runs", "config")
    op.drop_column("mcp_runs", "mode")

    op.drop_column("mcp_sessions", "metadata")

    op.drop_column("mcp_connections", "env")
    op.drop_column("mcp_connections", "config")

