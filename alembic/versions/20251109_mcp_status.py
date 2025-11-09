"""Update MCP connection status defaults and constraint.

Revision ID: 20251109_mcp_status
Revises: None
Create Date: 2025-11-09
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20251109_mcp_status"
down_revision = None
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


def upgrade():
    """Apply MCP status constraint changes."""
    # 기본값 수정
    op.execute("ALTER TABLE mcp_connections MODIFY (status DEFAULT 'pending')")

    # 기존 제약 제거 후 재생성
    _drop_constraint_if_exists("CHK_MCP_CONNECTION_STATUS")
    op.execute(
        """
        ALTER TABLE mcp_connections
        ADD CONSTRAINT chk_mcp_connection_status
        CHECK (status IN ('pending', 'active', 'inactive', 'error'))
        """
    )


def downgrade():
    """Revert MCP status constraint changes."""
    op.execute("ALTER TABLE mcp_connections MODIFY (status DEFAULT 'active')")

    _drop_constraint_if_exists("CHK_MCP_CONNECTION_STATUS")
    op.execute(
        """
        ALTER TABLE mcp_connections
        ADD CONSTRAINT chk_mcp_connection_status
        CHECK (status IN ('active', 'inactive', 'error'))
        """
    )

