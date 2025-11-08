"""MCP (Model Context Protocol) 서비스 골격."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session  # type: ignore

from app.core.exceptions import NotFoundError, ValidationError
from app.db import models

from app.schemas.mcp import (
    MCPConnectionCreate,
    MCPConnectionResponse,
    MCPRunCreate,
    MCPRunResponse,
    MCPRunStatusResponse,
    MCPSessionCreate,
    MCPSessionResponse,
)


class MCPService:
    """MCP 관련 도메인 로직을 담당하는 서비스."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------
    def create_connection(self, payload: MCPConnectionCreate) -> MCPConnectionResponse:
        """MCP 연결 생성."""
        project = self._get_project(payload.project_id)
        connection = models.MCPConnection(
            project_id=project.id,
            connection_type=payload.connection_type,
            status="active",
        )
        self.db.add(connection)
        self.db.commit()
        self.db.refresh(connection)
        return self._to_connection_response(connection)

    def list_connections(self, project_id: Optional[int] = None) -> List[MCPConnectionResponse]:
        """MCP 연결 목록 조회."""
        query = self.db.query(models.MCPConnection)
        if project_id is not None:
            query = query.filter(models.MCPConnection.project_id == project_id)
        connections = query.order_by(models.MCPConnection.created_at.desc()).all()
        return [self._to_connection_response(conn) for conn in connections]

    def deactivate_connection(self, connection_id: int) -> None:
        """MCP 연결 비활성화."""
        connection = self._get_connection(connection_id)
        connection.status = "inactive"
        self.db.add(connection)
        self.db.commit()

    # ------------------------------------------------------------------
    # Session
    # ------------------------------------------------------------------
    def create_session(self, payload: MCPSessionCreate) -> MCPSessionResponse:
        """MCP 세션 생성."""
        connection = self._get_connection(payload.connection_id)
        if connection.status != "active":
            raise ValidationError("비활성화된 연결에서는 세션을 생성할 수 없습니다.")

        session = models.MCPSession(
            connection_id=connection.id,
            status="active",
            context=self._dump_json(payload.context),
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return self._to_session_response(session)

    def list_sessions(self, connection_id: Optional[int] = None) -> List[MCPSessionResponse]:
        """MCP 세션 목록 조회."""
        query = self.db.query(models.MCPSession)
        if connection_id is not None:
            query = query.filter(models.MCPSession.connection_id == connection_id)
        sessions = query.order_by(models.MCPSession.created_at.desc()).all()
        return [self._to_session_response(session) for session in sessions]

    def close_session(self, session_id: int) -> None:
        """MCP 세션 종료."""
        session = self._get_session(session_id)
        session.status = "closed"
        self.db.add(session)
        self.db.commit()

    # ------------------------------------------------------------------
    # Catalog
    # ------------------------------------------------------------------
    def list_tools(self, session_id: int) -> Dict[str, Any]:
        """세션별 사용 가능한 MCP 툴 목록 조회."""
        raise NotImplementedError

    def list_resources(self, session_id: int) -> Dict[str, Any]:
        """세션별 리소스 목록 조회."""
        raise NotImplementedError

    def list_prompts(self, session_id: int) -> Dict[str, Any]:
        """세션별 프롬프트 목록 조회."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------
    def create_run(self, payload: MCPRunCreate) -> MCPRunResponse:
        """MCP 실행 생성."""
        raise NotImplementedError

    def get_run(self, run_id: int) -> MCPRunStatusResponse:
        """MCP 실행 상태 조회."""
        raise NotImplementedError

    def cancel_run(self, run_id: int) -> MCPRunStatusResponse:
        """MCP 실행 취소."""
        raise NotImplementedError

    def list_run_events(self, run_id: int) -> Dict[str, Any]:
        """MCP 실행 이벤트 목록."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_project(self, project_id: int) -> models.Project:
        project = self.db.query(models.Project).filter(models.Project.id == project_id).first()
        if not project:
            raise NotFoundError("Project", str(project_id))
        return project

    def _get_connection(self, connection_id: int) -> models.MCPConnection:
        connection = (
            self.db.query(models.MCPConnection)
            .filter(models.MCPConnection.id == connection_id)
            .first()
        )
        if not connection:
            raise NotFoundError("MCPConnection", str(connection_id))
        return connection

    def _get_session(self, session_id: int) -> models.MCPSession:
        session = (
            self.db.query(models.MCPSession)
            .filter(models.MCPSession.id == session_id)
            .first()
        )
        if not session:
            raise NotFoundError("MCPSession", str(session_id))
        return session

    def _build_setup_commands(self, connection: models.MCPConnection) -> List[str]:
        # TODO: 실제 CLI 토큰 발급 로직 연동 필요
        return [
            "npm i -g @atrina/cli",
            f"atrina init MCP-{connection.project_id}-{connection.id}",
        ]

    def _to_connection_response(self, connection: models.MCPConnection) -> MCPConnectionResponse:
        return MCPConnectionResponse(
            id=connection.id,
            project_id=connection.project_id,
            connection_type=connection.connection_type,
            status=connection.status,
            created_at=connection.created_at,
            updated_at=connection.updated_at,
            setup_commands=self._build_setup_commands(connection),
        )

    def _to_session_response(self, session: models.MCPSession) -> MCPSessionResponse:
        return MCPSessionResponse(
            id=session.id,
            connection_id=session.connection_id,
            status=session.status,
            context=self._load_json(session.context),
            created_at=session.created_at,
            updated_at=session.updated_at,
        )

    def _dump_json(self, payload: Optional[Dict[str, Any]]) -> Optional[str]:
        if payload is None:
            return None
        return json.dumps(payload, ensure_ascii=False)

    def _load_json(self, payload: Optional[str]) -> Optional[Dict[str, Any]]:
        if not payload:
            return None
        try:
            return json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValidationError(f"JSON 파싱에 실패했습니다: {exc}") from exc


