"""Cleanup MCP run table to match domain model.

Revision ID: 20251109_mcp_run_cleanup
Revises: 20251109_mcp_session_cleanup
Create Date: 2025-11-09
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20251109_mcp_run_cleanup"
down_revision = "20251109_mcp_session_cleanup"
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
                EXECUTE IMMEDIATE 'ALTER TABLE mcp_runs DROP CONSTRAINT {name}';
            END IF;
        END;
        """
    )


def upgrade():
    # 기존 run_mode, config_json 등 레거시 컬럼 제거
    for col in ["run_mode", "config_json", "input_json", "output_json", "error_json", "started_at", "finished_at"]:
        op.execute(
            f"""
            DECLARE
                v_cnt INTEGER;
            BEGIN
                SELECT COUNT(*)
                  INTO v_cnt
                  FROM user_tab_cols
                 WHERE table_name = 'MCP_RUNS'
                   AND column_name = '{col.upper()}';

                IF v_cnt = 1 THEN
                    EXECUTE IMMEDIATE 'ALTER TABLE mcp_runs DROP COLUMN {col}';
                END IF;
            END;
            """
        )

    _drop_index_if_exists("IX_MCP_RUNS_MODE")

    _drop_constraint_if_exists("CK_MCP_RUNS_RUN_MODE")
    _drop_constraint_if_exists("CK_MCP_RUNS_STATUS")

    op.execute(
        """
        DECLARE
            v_cnt INTEGER;
        BEGIN
            SELECT COUNT(*) INTO v_cnt FROM user_tab_cols WHERE table_name = 'MCP_RUNS' AND column_name = 'MODE';
            IF v_cnt = 0 THEN
                EXECUTE IMMEDIATE 'ALTER TABLE mcp_runs ADD (mode VARCHAR2(50))';
            END IF;

            SELECT COUNT(*) INTO v_cnt FROM user_tab_cols WHERE table_name = 'MCP_RUNS' AND column_name = 'CONFIG';
            IF v_cnt = 0 THEN
                EXECUTE IMMEDIATE 'ALTER TABLE mcp_runs ADD (config CLOB)';
            END IF;

            SELECT COUNT(*) INTO v_cnt FROM user_tab_cols WHERE table_name = 'MCP_RUNS' AND column_name = 'ARGUMENTS';
            IF v_cnt = 0 THEN
                EXECUTE IMMEDIATE 'ALTER TABLE mcp_runs ADD (arguments CLOB)';
            END IF;

            SELECT COUNT(*) INTO v_cnt FROM user_tab_cols WHERE table_name = 'MCP_RUNS' AND column_name = 'PROGRESS';
            IF v_cnt = 0 THEN
                EXECUTE IMMEDIATE 'ALTER TABLE mcp_runs ADD (progress VARCHAR2(20))';
            END IF;

            SELECT COUNT(*) INTO v_cnt FROM user_tab_cols WHERE table_name = 'MCP_RUNS' AND column_name = 'MESSAGE';
            IF v_cnt = 0 THEN
                EXECUTE IMMEDIATE 'ALTER TABLE mcp_runs ADD (message CLOB)';
            END IF;

            SELECT COUNT(*) INTO v_cnt FROM user_tab_cols WHERE table_name = 'MCP_RUNS' AND column_name = 'RESULT';
            IF v_cnt = 0 THEN
                EXECUTE IMMEDIATE 'ALTER TABLE mcp_runs ADD (result CLOB)';
            END IF;
        END;
        """
    )

    # 기존 데이터가 있다면 애플리케이션에서 재저장 시 채워질 수 있으므로 DB 레벨에서 강제 업데이트는 생략

    op.execute(
        """
        ALTER TABLE mcp_runs
        ADD CONSTRAINT chk_mcp_runs_status
        CHECK (status IN ('queued','running','succeeded','failed','cancelled'))
        """
    )


def downgrade():
    op.execute("ALTER TABLE mcp_runs DROP COLUMN message")
    op.execute("ALTER TABLE mcp_runs DROP COLUMN progress")
    op.execute("ALTER TABLE mcp_runs DROP COLUMN arguments")
    op.execute("ALTER TABLE mcp_runs DROP COLUMN config")
    op.execute("ALTER TABLE mcp_runs DROP COLUMN result")
    op.execute("ALTER TABLE mcp_runs DROP COLUMN mode")

    op.execute(
        """
        ALTER TABLE mcp_runs
        ADD (run_mode VARCHAR2(10) DEFAULT 'chat', config_json CLOB, input_json CLOB, output_json CLOB, error_json CLOB, started_at TIMESTAMP WITH TIME ZONE, finished_at TIMESTAMP WITH TIME ZONE)
        """
    )

    op.execute(
        """
        ALTER TABLE mcp_runs
        ADD CONSTRAINT ck_mcp_runs_run_mode
        CHECK (run_mode IN ('chat','tool','prompt'))
        """
    )

