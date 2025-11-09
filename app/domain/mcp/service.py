"""MCP (Model Context Protocol) 서비스 골격."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session  # type: ignore

from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError
from app.db import models
from app.domain.mcp.providers import ChatGPTProvider

from app.schemas.mcp import (
    MCPConnectionCreate,
    MCPConnectionResponse,
    MCPProjectStatusResponse,
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
            status="pending",
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
    _TOOL_REGISTRY: Dict[str, List[Dict[str, Any]]] = {
        "cursor": [
            {
                "name": "syncTasks",
                "description": "프로젝트 태스크를 Cursor와 동기화합니다.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "force": {
                            "type": "boolean",
                            "description": "이미 동기화된 태스크를 재강제할지 여부",
                        }
                    },
                },
            }
        ],
        "claude": [
            {
                "name": "summarizeRequirements",
                "description": "중요 요구사항을 요약합니다.",
            }
        ],
        "chatgpt": [
            {
                "name": "draftMeetingNotes",
                "description": "회의록 초안을 생성합니다.",
            }
        ],
    }

    _RESOURCE_REGISTRY: Dict[str, List[Dict[str, Any]]] = {
        "cursor": [
            {
                "uri": "project://tasks",
                "name": "프로젝트 태스크",
                "description": "Cursor 프로젝트에 등록된 태스크 목록",
            }
        ],
        "claude": [
            {
                "uri": "knowledge://architecture",
                "name": "아키텍처 문서",
                "description": "최신 시스템 아키텍처 요약",
            }
        ],
        "chatgpt": [
            {
                "uri": "knowledge://guideline",
                "name": "개발 가이드",
                "description": "팀 개발 가이드라인",
            }
        ],
    }

    _PROMPT_REGISTRY: Dict[str, List[Dict[str, Any]]] = {
        "cursor": [
            {
                "name": "implementFeature",
                "description": "주어진 요구사항을 구현하는 제안서를 생성합니다.",
                "arguments": [
                    {"name": "requirement", "type": "string", "description": "요구사항"},
                ],
            }
        ],
        "claude": [
            {
                "name": "brainstormIdeas",
                "description": "새로운 기능 아이디어를 브레인스토밍합니다.",
            }
        ],
        "chatgpt": [
            {
                "name": "writeTestCases",
                "description": "테스트 케이스 초안을 작성합니다.",
            }
        ],
    }

    def list_tools(self, session_id: int) -> Dict[str, Any]:
        """세션별 사용 가능한 MCP 툴 목록 조회."""
        session = self._get_session(session_id)
        connection_type = session.connection.connection_type
        tools = self._TOOL_REGISTRY.get(connection_type, [])
        return {"items": tools, "total": len(tools)}

    def list_resources(self, session_id: int) -> Dict[str, Any]:
        """세션별 리소스 목록 조회."""
        session = self._get_session(session_id)
        connection_type = session.connection.connection_type
        resources = self._RESOURCE_REGISTRY.get(connection_type, [])
        return {"items": resources, "total": len(resources)}

    def list_prompts(self, session_id: int) -> Dict[str, Any]:
        """세션별 프롬프트 목록 조회."""
        session = self._get_session(session_id)
        connection_type = session.connection.connection_type
        prompts = self._PROMPT_REGISTRY.get(connection_type, [])
        return {"items": prompts, "total": len(prompts)}

    # ------------------------------------------------------------------
    # Project status
    # ------------------------------------------------------------------
    def list_project_statuses(self) -> List[MCPProjectStatusResponse]:
        """프로젝트별 MCP 상태 요약."""
        projects = self.db.query(models.Project).all()
        results: List[MCPProjectStatusResponse] = []
        for project in projects:
            status = self._resolve_project_status(project.mcp_connections)
            results.append(
                MCPProjectStatusResponse(
                    id=str(project.id),
                    name=project.name,
                    mcpStatus=status,
                )
            )
        return results

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------
    def create_run(self, payload: MCPRunCreate) -> MCPRunResponse:
        """MCP 실행 생성."""
        session = self._get_session(payload.session_id)
        if session.status != "active":
            raise ValidationError("비활성화된 세션에서는 실행을 생성할 수 없습니다.")

        run = models.MCPRun(
            session_id=session.id,
            tool_name=payload.tool_name,
            prompt_name=payload.prompt_name,
            arguments=self._dump_json(payload.arguments),
            status="running" if payload.tool_name or payload.prompt_name else "pending",
            progress="0.0",
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)

        try:
            self._execute_run(session, run, payload.arguments or {})
        except ValidationError:
            raise
        except Exception as exc:  # pylint: disable=broad-except
            run.status = "failed"
            run.message = str(exc)
        finally:
            self.db.add(run)
            self.db.commit()
            self.db.refresh(run)

        return self._to_run_response(run)

    def get_run(self, run_id: int) -> MCPRunStatusResponse:
        """MCP 실행 상태 조회."""
        run = self._get_run(run_id)
        return self._to_run_status_response(run)

    def cancel_run(self, run_id: int) -> MCPRunStatusResponse:
        """MCP 실행 취소."""
        run = self._get_run(run_id)
        if run.status in {"completed", "failed", "cancelled"}:
            raise ValidationError("이미 종료된 실행입니다.")
        run.status = "cancelled"
        run.message = "사용자 요청으로 실행이 취소되었습니다."
        run.progress = "0.0"
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return self._to_run_status_response(run)

    def list_run_events(self, run_id: int) -> Dict[str, Any]:
        """MCP 실행 이벤트 목록."""
        run = self._get_run(run_id)
        events = [
            {
                "type": "status",
                "status": run.status,
                "progress": self._as_float(run.progress),
                "message": run.message,
            }
        ]
        return {"items": events, "total": len(events)}

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

    def _get_run(self, run_id: int) -> models.MCPRun:
        run = self.db.query(models.MCPRun).filter(models.MCPRun.id == run_id).first()
        if not run:
            raise NotFoundError("MCPRun", str(run_id))
        return run

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

    def _dump_json(self, payload: Optional[Any]) -> Optional[str]:
        if payload is None:
            return None
        return json.dumps(payload, ensure_ascii=False)

    def _load_json(self, payload: Optional[str]) -> Optional[Any]:
        if not payload:
            return None
        try:
            return json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValidationError(f"JSON 파싱에 실패했습니다: {exc}") from exc

    def _to_run_response(self, run: models.MCPRun) -> MCPRunResponse:
        return MCPRunResponse(
            id=run.id,
            session_id=run.session_id,
            status=run.status,
            result=self._load_json(run.result),
            arguments=self._load_json(run.arguments),
            progress=self._as_float(run.progress),
            message=run.message,
            created_at=run.created_at,
            updated_at=run.updated_at,
        )

    def _to_run_status_response(self, run: models.MCPRun) -> MCPRunStatusResponse:
        return MCPRunStatusResponse(
            id=run.id,
            status=run.status,
            progress=self._as_float(run.progress),
            message=run.message,
            result=self._load_json(run.result),
        )

    def _as_float(self, value: Optional[str]) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _resolve_project_status(
        self, connections: List[models.MCPConnection]
    ) -> Optional[str]:
        if not connections:
            return None

        if any(conn.status == "active" for conn in connections):
            return "connected"

        if any(conn.status == "pending" for conn in connections):
            return "pending"

        if any(conn.status == "error" for conn in connections):
            return "pending"

        return None

    def _execute_run(
        self,
        session: models.MCPSession,
        run: models.MCPRun,
        arguments: Dict[str, Any],
    ) -> None:
        """Execute run according to the connection type."""
        connection_type = session.connection.connection_type

        if connection_type == "chatgpt":
            if not settings.openai_api_key:
                raise ValidationError("ChatGPT 실행을 위해 OPENAI_API_KEY 환경 변수가 필요합니다.")

            provider = ChatGPTProvider(
                api_key=settings.openai_api_key,
                model=settings.openai_model,
            )

            try:
                result_payload = provider.run(arguments)
            except ValueError as exc:
                raise ValidationError(str(exc)) from exc

            run.result = self._dump_json(result_payload)
            run.status = "completed"
            run.progress = "1.0"
            run.message = "ChatGPT 응답이 생성되었습니다."
        else:
            run.status = "completed"
            run.progress = "1.0"
            run.message = "실행이 기록되었습니다. (외부 연결 미구현)"



