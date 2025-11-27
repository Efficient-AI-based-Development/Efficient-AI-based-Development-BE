"""MCP (Model Context Protocol) 서비스 골격."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session  # type: ignore

from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError
from app.db import models
from app.domain.mcp.providers import ChatGPTProvider, ClaudeProvider, CursorProvider
from app.schemas.mcp import (
    MCPConnectionCreate,
    MCPConnectionData,
    MCPConfigFileResponse,
    MCPGuideCommand,
    MCPGuidePlatform,
    MCPGuideResponse,
    MCPGuideStep,
    MCPProjectStatusItem,
    MCPPromptItem,
    MCPResourceItem,
    MCPRunCreate,
    MCPRunData,
    MCPRunStatusData,
    MCPSessionCreate,
    MCPSessionData,
    MCPTaskCommandResponse,
    MCPToolItem,
)
from app.schemas.task import StartDevelopmentRequest


COMMON_TOOLS: list[dict[str, Any]] = [
    {
        "toolId": "start_development",
        "name": "Start Development",
        "description": "태스크 ID를 받아 PRD/SRS/USER_STORY 문서와 태스크 정보를 수집하여 코드 구현을 시작합니다. 문서와 태스크 컨텍스트를 자동으로 활용합니다.",
        "inputSchema": {
            "type": "object",
            "required": ["taskId"],
            "properties": {
                "taskId": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "코드 구현을 시작할 태스크 ID",
                },
                "providerId": {
                    "type": "string",
                    "description": "선택적 provider (chatgpt/claude/cursor)",
                },
                "options": {
                    "type": "object",
                    "description": "mode, temperature 등 추가 옵션 (선택)",
                },
            },
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "taskId": {"type": "integer"},
                "sessionId": {"type": "string"},
                "runId": {"type": "string"},
                "status": {"type": "string"},
                "preview": {"type": "string"},
                "summary": {"type": ["string", "null"]},
                "providerId": {"type": "string"},
                "context": {
                    "type": "object",
                    "description": "수집된 컨텍스트 정보 (태스크, 문서, 프로젝트)",
                },
            },
        },
    },
    {
        "toolId": "generate_code",
        "name": "Generate Code",
        "description": "태스크와 관련 문서(PRD/SRS/USER_STORY)를 기반으로 코드를 생성합니다. 기존 코드베이스 구조를 참고하여 구현합니다.",
        "inputSchema": {
            "type": "object",
            "required": ["taskId"],
            "properties": {
                "taskId": {
                    "type": "integer",
                    "description": "코드를 생성할 태스크 ID",
                },
                "filePath": {
                    "type": "string",
                    "description": "생성할 파일 경로 (선택, 없으면 자동 결정)",
                },
                "options": {
                    "type": "object",
                    "description": "생성 옵션 (language, framework 등)",
                },
            },
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "taskId": {"type": "integer"},
                "generatedFiles": {"type": "array", "items": {"type": "string"}},
                "codePreview": {"type": "string"},
                "status": {"type": "string"},
            },
        },
    },
    {
        "toolId": "review_code",
        "name": "Code Review",
        "description": "생성된 코드를 리뷰하고 개선 사항을 제안합니다. 태스크 요구사항과 문서를 기준으로 검토합니다.",
        "inputSchema": {
            "type": "object",
            "required": ["taskId"],
            "properties": {
                "taskId": {
                    "type": "integer",
                    "description": "리뷰할 태스크 ID",
                },
                "filePaths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "리뷰할 파일 경로 목록 (선택, 없으면 태스크 관련 파일 전체)",
                },
            },
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "taskId": {"type": "integer"},
                "reviewedFiles": {"type": "array", "items": {"type": "string"}},
                "issues": {"type": "array", "items": {"type": "object"}},
                "suggestions": {"type": "array", "items": {"type": "string"}},
                "status": {"type": "string"},
            },
        },
    },
    {
        "toolId": "sync_tasks",
        "name": "Sync Task Board",
        "description": "프로젝트의 최신 태스크 상태를 동기화합니다.",
        "inputSchema": {"type": "object"},
        "outputSchema": {
            "type": "object",
            "properties": {
                "synced": {"type": "boolean"},
                "task_count": {"type": "integer"},
                "tasks": {"type": "array", "items": {"type": "object"}},
            },
        },
    },
]

COMMON_RESOURCES: list[dict[str, Any]] = [
    {
        "uri": "project://tasks",
        "kind": "tasks",
        "description": "프로젝트 전체 태스크 목록",
    },
    {
        "uri": "project://documents",
        "kind": "documents",
        "description": "모든 프로젝트 문서 목록",
    },
    {
        "uri": "project://documents/PRD",
        "kind": "documents",
        "description": "최신 PRD 문서",
    },
    {
        "uri": "project://documents/SRS",
        "kind": "documents",
        "description": "시스템 요구사항(SRS) 문서",
    },
    {
        "uri": "project://documents/USER_STORY",
        "kind": "documents",
        "description": "등록된 사용자 스토리",
    },
]

COMMON_PROMPTS: list[dict[str, Any]] = [
    {
        "promptId": "start_dev_plan",
        "name": "개발 플랜 검토",
        "description": "Start Development 전에 고수준 계획을 정리할 때 사용합니다.",
    },
    {
        "promptId": "risk_review",
        "name": "리스크 리뷰",
        "description": "태스크 위험 요소와 대응 전략을 점검합니다.",
    },
]


class MCPService:
    """MCP 관련 도메인 로직을 담당하는 서비스."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------
    def create_connection(self, payload: MCPConnectionCreate) -> MCPConnectionData:
        """MCP 연결 생성."""
        project_id = self._parse_project_identifier(payload.project_id)
        project = self._get_project(project_id)

        connection = models.MCPConnection(
            project_id=project.id,
            connection_type=payload.provider_id,
            status="pending",
            config=self._dump_json(payload.config),
            env=self._dump_json(payload.env),
        )
        self.db.add(connection)
        self.db.commit()
        self.db.refresh(connection)

        return self._to_connection_data(connection)

    def list_connections(self, project_identifier: str | None = None) -> list[MCPConnectionData]:
        """MCP 연결 목록 조회."""
        query = self.db.query(models.MCPConnection)
        if project_identifier is not None:
            project_id = self._parse_project_identifier(project_identifier)
            query = query.filter(models.MCPConnection.project_id == project_id)
        connections = query.order_by(models.MCPConnection.created_at.desc()).all()
        return [self._to_connection_data(conn) for conn in connections]

    def deactivate_connection(self, external_connection_id: str) -> dict[str, Any]:
        """MCP 연결 비활성화."""
        connection_id = self._decode_connection_id(external_connection_id, prefix="cn")
        connection = self._get_connection(connection_id)
        connection.status = "inactive"
        self.db.add(connection)
        self.db.commit()
        return {
            "closed": True,
            "connectionId": external_connection_id,
        }

    def activate_connection(self, external_connection_id: str) -> MCPConnectionData:
        """MCP 연결 활성화."""
        connection_id = self._decode_connection_id(external_connection_id, prefix="cn")
        connection = self._get_connection(connection_id)
        connection.status = "active"
        self.db.add(connection)
        self.db.commit()
        self.db.refresh(connection)
        return self._to_connection_data(connection)

    # ------------------------------------------------------------------
    # Session
    # ------------------------------------------------------------------
    def create_session(self, payload: MCPSessionCreate) -> MCPSessionData:
        """MCP 세션 생성."""
        try:
            connection_id = self._decode_connection_id(payload.connection_id, prefix="cn")
        except ValidationError as exc:
            raise ValidationError(f"연결 ID 형식이 올바르지 않습니다: {payload.connection_id}. {exc.message}") from exc
        
        try:
            connection = self._get_connection(connection_id)
        except NotFoundError as exc:
            raise ValidationError(f"연결을 찾을 수 없습니다: {payload.connection_id}") from exc
        
        if connection.status not in {"connected", "active"}:
            raise ValidationError(
                f"활성화된 MCP 연결에서만 세션을 시작할 수 있습니다. "
                f"현재 연결 상태: {connection.status}. "
                f"연결을 활성화하려면 POST /api/v1/mcp/connections/{payload.connection_id}/activate 를 호출하세요."
            )

        try:
            session = models.MCPSession(
                connection_id=connection.id,
                project_id=connection.project_id,  # 연결의 프로젝트 ID 사용
                status="ready",
                context=self._dump_json({}),
                metadata_json=self._dump_json(payload.metadata),
            )
            self.db.add(session)
            self.db.commit()
            self.db.refresh(session)
            return self._to_session_data(session)
        except Exception as exc:
            self.db.rollback()
            raise ValidationError(f"세션 생성 중 오류가 발생했습니다: {str(exc)}") from exc

    def list_sessions(self, connection_identifier: str | None = None) -> list[MCPSessionData]:
        """MCP 세션 목록 조회."""
        query = self.db.query(models.MCPSession)
        if connection_identifier is not None:
            connection_id = self._decode_connection_id(connection_identifier, prefix="cn")
            query = query.filter(models.MCPSession.connection_id == connection_id)
        sessions = query.order_by(models.MCPSession.created_at.desc()).all()
        return [self._to_session_data(session) for session in sessions]

    def close_session(self, external_session_id: str) -> dict[str, Any]:
        """MCP 세션 종료."""
        session_id = self._decode_connection_id(external_session_id, prefix="ss")
        session = self._get_session(session_id)
        session.status = "closed"
        self.db.add(session)
        self.db.commit()
        return {
            "closed": True,
            "sessionId": external_session_id,
        }

    # ------------------------------------------------------------------
    # Catalog
    # ------------------------------------------------------------------
    _TOOL_REGISTRY: dict[str, list[dict[str, Any]]] = {
        provider: [dict(tool) for tool in COMMON_TOOLS]
        for provider in ("chatgpt", "cursor", "claude")
    }

    _RESOURCE_REGISTRY: dict[str, list[dict[str, Any]]] = {
        provider: [dict(resource) for resource in COMMON_RESOURCES]
        for provider in ("chatgpt", "cursor", "claude")
    }

    _PROMPT_REGISTRY: dict[str, list[dict[str, Any]]] = {
        provider: [dict(prompt) for prompt in COMMON_PROMPTS]
        for provider in ("chatgpt", "cursor", "claude")
    }

    def list_tools(self, external_session_id: str) -> list[MCPToolItem]:
        """세션별 사용 가능한 MCP 툴 목록 조회."""
        session_id = self._decode_connection_id(external_session_id, prefix="ss")
        session = self._get_session(session_id)
        connection_type = session.connection.connection_type
        tools = self._TOOL_REGISTRY.get(connection_type, [])
        return [MCPToolItem(**tool) for tool in tools]

    def list_resources(self, external_session_id: str) -> list[MCPResourceItem]:
        """세션별 리소스 목록 조회."""
        session_id = self._decode_connection_id(external_session_id, prefix="ss")
        session = self._get_session(session_id)
        connection_type = session.connection.connection_type
        resources = self._RESOURCE_REGISTRY.get(connection_type, [])
        return [MCPResourceItem(**resource) for resource in resources]

    def read_resource(self, external_session_id: str, uri: str) -> dict[str, Any]:
        """리소스 읽기."""
        session_id = self._decode_connection_id(external_session_id, prefix="ss")
        session = self._get_session(session_id)
        project_id = session.connection.project_id

        if uri.startswith("file:///"):
            # 파일 리소스 읽기
            file_path = uri.replace("file:///", "")
            return self._read_file_resource(file_path)
        elif uri.startswith("search:///"):
            # 검색 리소스
            query = uri.replace("search:///", "").split("?query=")
            search_query = query[1] if len(query) > 1 else ""
            return self._read_search_resource(search_query, project_id)
        elif uri.startswith("project://"):
            # 프로젝트 리소스
            resource_type = uri.replace("project://", "")
            return self._read_project_resource(resource_type, project_id)
        else:
            raise ValidationError(f"지원하지 않는 리소스 URI 형식: {uri}")

    def _read_file_resource(self, file_path: str) -> dict[str, Any]:
        """파일 리소스 읽기."""
        # 실제 파일 시스템에서 읽기 (예: README.md)
        from pathlib import Path

        # 프로젝트 루트 기준으로 파일 읽기
        project_root = Path.cwd()
        target_file = project_root / file_path.lstrip("/")

        if not target_file.exists():
            raise NotFoundError("File", file_path)

        try:
            content = target_file.read_text(encoding="utf-8")
            return {
                "uri": f"file:///{file_path}",
                "kind": "file",
                "content": content,
                "size": len(content),
            }
        except Exception as exc:
            raise ValidationError(f"파일 읽기 실패: {str(exc)}") from exc

    def _read_search_resource(self, query: str, project_id: int) -> dict[str, Any]:
        """검색 리소스 읽기."""
        # 태스크나 문서에서 검색
        results = []

        # 태스크 검색
        tasks = (
            self.db.query(models.Task)
            .filter(
                models.Task.project_id == project_id,
                models.Task.title.ilike(f"%{query}%"),
            )
            .limit(10)
            .all()
        )
        for task in tasks:
            results.append({
                "type": "task",
                "id": task.id,
                "title": task.title,
                "status": task.status,
            })

        # 문서 검색
        documents = (
            self.db.query(models.Document)
            .filter(
                models.Document.project_id == project_id,
                models.Document.title.ilike(f"%{query}%"),
            )
            .limit(10)
            .all()
        )
        for doc in documents:
            results.append({
                "type": "document",
                "id": doc.id,
                "title": doc.title,
                "doc_type": doc.type,
            })

        return {
            "uri": f"search:///code?query={query}",
            "kind": "search",
            "query": query,
            "results": results,
            "count": len(results),
        }

    def _read_project_resource(self, resource_type: str, project_id: int) -> dict[str, Any]:
        """프로젝트 리소스 읽기."""
        if resource_type == "tasks":
            tasks = (
                self.db.query(models.Task)
                .filter(models.Task.project_id == project_id)
                .order_by(models.Task.updated_at.desc())
                .all()
            )
            return {
                "uri": "project://tasks",
                "kind": "tasks",
                "tasks": [
                    {
                        "id": task.id,
                        "title": task.title,
                        "status": task.status,
                        "type": task.type,
                        "priority": task.priority,
                    }
                    for task in tasks
                ],
                "count": len(tasks),
            }
        elif resource_type == "documents":
            documents = (
                self.db.query(models.Document)
                .filter(models.Document.project_id == project_id)
                .order_by(models.Document.updated_at.desc())
                .all()
            )
            return {
                "uri": "project://documents",
                "kind": "documents",
                "documents": [
                    {
                        "id": doc.id,
                        "title": doc.title,
                        "type": doc.type,
                        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
                        "preview": (doc.content_md or "")[:160],
                    }
                    for doc in documents
                ],
                "count": len(documents),
            }
        elif resource_type.startswith("documents/"):
            _, doc_type_raw = resource_type.split("/", 1)
            doc_type = doc_type_raw.upper()
            documents = (
                self.db.query(models.Document)
                .filter(
                    models.Document.project_id == project_id,
                    models.Document.type == doc_type,
                )
                .order_by(models.Document.updated_at.desc())
                .all()
            )
            return {
                "uri": f"project://documents/{doc_type}",
                "kind": "documents",
                "doc_type": doc_type,
                "documents": [
                    {
                        "id": doc.id,
                        "title": doc.title,
                        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
                        "preview": (doc.content_md or "")[:400],
                    }
                    for doc in documents
                ],
                "count": len(documents),
            }
        else:
            raise ValidationError(f"알 수 없는 프로젝트 리소스 타입: {resource_type}")

    def list_prompts(self, external_session_id: str) -> list[MCPPromptItem]:
        """세션별 프롬프트 목록 조회."""
        session_id = self._decode_connection_id(external_session_id, prefix="ss")
        session = self._get_session(session_id)
        connection_type = session.connection.connection_type
        prompts = self._PROMPT_REGISTRY.get(connection_type, [])
        return [MCPPromptItem(**prompt) for prompt in prompts]

    # ------------------------------------------------------------------
    # Project status
    # ------------------------------------------------------------------
    def list_project_statuses(self) -> list[MCPProjectStatusItem]:
        """프로젝트별 MCP 상태 요약."""
        projects = self.db.query(models.Project).all()
        result = []
        for project in projects:
            # 활성 세션 개수 확인
            active_sessions_count = (
                self.db.query(models.MCPSession)
                .join(models.MCPConnection)
                .filter(
                    models.MCPConnection.project_id == project.id,
                    models.MCPSession.status.in_(["ready", "active"]),
                )
                .count()
            )
            
            result.append(
            MCPProjectStatusItem(
                id=str(project.id),
                name=project.title,  # Project 모델의 title 필드 사용
                mcp_status=self._resolve_project_status(project.mcp_connections),
                    has_active_session=active_sessions_count > 0,
            )
            )
        return result

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------
    def create_run(self, payload: MCPRunCreate) -> MCPRunData:
        """MCP 실행 생성."""
        session_id = self._decode_connection_id(payload.session_id, prefix="ss")
        session = self._get_session(session_id)
        if session.status not in {"ready", "active"}:
            raise ValidationError("세션이 준비 상태가 아니어서 실행을 시작할 수 없습니다.")

        run = models.MCPRun(
            session_id=session.id,
            task_id=payload.task_id,
            tool_name=payload.tool_id,
            prompt_name=payload.prompt_id,
            mode=payload.mode,
            status="queued",
            config=self._dump_json(payload.config),
            arguments=self._dump_json(payload.input),
            progress="0.0",
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)

        self._execute_run(session, run, payload)
        return self._to_run_data(run)

    def get_run(self, external_run_id: str) -> MCPRunStatusData:
        """MCP 실행 상태 조회."""
        run_id = self._decode_connection_id(external_run_id, prefix="run")
        run = self._get_run(run_id)
        return self._to_run_status_data(run)

    def cancel_run(self, external_run_id: str) -> dict[str, Any]:
        """MCP 실행 취소."""
        run_id = self._decode_connection_id(external_run_id, prefix="run")
        run = self._get_run(run_id)
        if self._map_run_status(run.status) in {"succeeded", "failed", "cancelled"}:
            raise ValidationError("이미 종료된 실행입니다.")
        run.status = "cancelled"
        run.message = "사용자 요청으로 실행이 취소되었습니다."
        run.progress = "0.0"
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return {
            "cancelled": True,
            "runId": external_run_id,
        }

    def list_run_events(self, external_run_id: str) -> list[dict[str, Any]]:
        """MCP 실행 이벤트 목록."""
        run_id = self._decode_connection_id(external_run_id, prefix="run")
        run = self._get_run(run_id)
        result_payload = self._load_json(run.result)

        events: list[dict[str, Any]] = [
            {
                "event": "RUN_STATUS",
                "data": {
                    "status": self._map_run_status(run.status),
                    "message": run.message,
                },
            }
        ]
        if isinstance(result_payload, dict):
            events.append(
                {
                    "event": "RUN_RESULT",
                    "data": result_payload,
                }
            )
        return events

    # ------------------------------------------------------------------
    # Guide
    # ------------------------------------------------------------------

    _GUIDES: dict[str, MCPGuideResponse] = {
        "chatgpt": MCPGuideResponse(
            provider_id="chatgpt",
            provider_name="ChatGPT MCP",
            supported_agents=["Cursor", "Claude Code", "Codex CLI"],
            prerequisites=[
                "Node.js 20 이상 설치",
                "fastmcp 서버 접근 토큰 (서비스에서 발급)",
            ],
            platforms=[
                MCPGuidePlatform(
                    os="macOS",
                    steps=[
                        MCPGuideStep(
                            title="1. MCP 서버 연결하기",
                            description="fastmcp CLI를 설치하고 로그인합니다. 계정당 한 번만 실행하면 됩니다.",
                            commands=[
                                MCPGuideCommand(text="npm i -g fastmcp-cli"),
                                MCPGuideCommand(text="fastmcp login --base-url <FASTMCP_URL>"),
                            ],
                        ),
                        MCPGuideStep(
                            title="2. 내 프로젝트 연동하기",
                            description="프로젝트 루트에서 fastmcp 프로젝트 설정을 생성합니다.",
                            commands=[
                                MCPGuideCommand(text="cd /path/to/project"),
                                MCPGuideCommand(text="fastmcp init --provider chatgpt --project <PROJECT_ID>"),
                            ],
                        ),
                        MCPGuideStep(
                            title="3. 에이전트에서 실행",
                            description="태스크에서의 명령을 실행하거나 UI 버튼을 눌러주세요. 자연어 명령어도 지원합니다.",
                            commands=[
                                MCPGuideCommand(text='fastmcp run "프로젝트 <PROJECT_ID>의 다음 작업 진행"'),
                                MCPGuideCommand(text='fastmcp run "이번 sprint 요약해줘"'),
                            ],
                        ),
                    ],
                ),
                MCPGuidePlatform(
                    os="Windows",
                    steps=[
                        MCPGuideStep(
                            title="1. MCP 서버 연결하기",
                            description="PowerShell에서 실행하세요. Node.js와 npm이 설치되어 있어야 합니다.",
                            commands=[
                                MCPGuideCommand(text="npm i -g fastmcp-cli"),
                                MCPGuideCommand(text="fastmcp login --api-key <OPENAI_API_KEY>"),
                            ],
                        ),
                        MCPGuideStep(
                            title="2. 프로젝트 연동하기",
                            description="PowerShell에서 프로젝트 디렉토리로 이동 후 초기화합니다.",
                            commands=[
                                MCPGuideCommand(text="cd C:\\path\\to\\project"),
                                MCPGuideCommand(text="fastmcp init --provider chatgpt --project <PROJECT_ID>"),
                            ],
                        ),
                        MCPGuideStep(
                            title="3. 명령 실행하기",
                            description="태스크에서의 명령을 실행하거나 UI 버튼을 눌러주세요. 자연어 명령어도 지원합니다.",
                            commands=[
                                MCPGuideCommand(text='fastmcp run "프로젝트 <PROJECT_ID>의 다음 작업 진행"'),
                                MCPGuideCommand(text='fastmcp run "이번 sprint 요약해줘"'),
                            ],
                        ),
                    ],
                ),
            ],
        ),
        "claude": MCPGuideResponse(
            provider_id="claude",
            provider_name="Claude Code MCP",
            supported_agents=["Claude Code", "Cursor"],
            prerequisites=[
                "Node.js 20 이상 설치",
                "Anthropic API Key 준비",
            ],
            platforms=[
                MCPGuidePlatform(
                    os="macOS",
                    steps=[
                        MCPGuideStep(
                            title="1. MCP 서버 연결하기",
                            description="fastmcp CLI를 통해 Anthropic 키로 로그인합니다.",
                            commands=[
                                MCPGuideCommand(text="npm i -g fastmcp-cli"),
                                MCPGuideCommand(text="fastmcp login --provider claude --api-key <ANTHROPIC_API_KEY>"),
                            ],
                        ),
                        MCPGuideStep(
                            title="2. 프로젝트 연동하기",
                            description="프로젝트 루트에서 Claude MCP 구성을 생성합니다.",
                            commands=[
                                MCPGuideCommand(text="cd /path/to/project"),
                                MCPGuideCommand(text="fastmcp init --provider claude --project <PROJECT_ID>"),
                            ],
                        ),
                        MCPGuideStep(
                            title="3. 에이전트 실행",
                            description="태스크에서의 명령을 실행하거나 UI 버튼을 눌러주세요. 자연어 명령어도 지원합니다.",
                            commands=[
                                MCPGuideCommand(text='fastmcp run "프로젝트 <PROJECT_ID>의 다음 작업 진행"'),
                                MCPGuideCommand(text='fastmcp run "이번 sprint 요약해줘"'),
                            ],
                        ),
                    ],
                ),
                MCPGuidePlatform(
                    os="Windows",
                    steps=[
                        MCPGuideStep(
                            title="PowerShell에서 로그인",
                            description="PowerShell을 관리자 권한으로 실행해 주세요.",
                            commands=[
                                MCPGuideCommand(text="npm i -g fastmcp-cli"),
                                MCPGuideCommand(text="fastmcp login --base-url <FASTMCP_URL>"),
                            ],
                        ),
                        MCPGuideStep(
                            title="프로젝트 초기화",
                            description="프로젝트 디렉토리에서 초기화합니다.",
                            commands=[
                                MCPGuideCommand(text="cd C:\\path\\to\\project"),
                                MCPGuideCommand(text="fastmcp init --provider claude --project <PROJECT_ID>"),
                            ],
                        ),
                        MCPGuideStep(
                            title="작업 실행",
                            description="태스크에서의 명령을 실행하거나 UI 버튼을 눌러주세요. 자연어 명령어도 지원합니다.",
                            commands=[
                                MCPGuideCommand(text='fastmcp run "프로젝트 <PROJECT_ID>의 다음 작업 진행"'),
                                MCPGuideCommand(text='fastmcp run "이번 sprint 요약해줘"'),
                            ],
                        ),
                    ],
                ),
            ],
        ),
        "cursor": MCPGuideResponse(
            provider_id="cursor",
            provider_name="Cursor MCP",
            supported_agents=["Cursor"],
            prerequisites=[
                "Node.js 20 이상 설치",
                "Cursor 0.45 이상 버전",
            ],
            platforms=[
                MCPGuidePlatform(
                    os="macOS",
                    steps=[
                        MCPGuideStep(
                            title="1. CLI 설치",
                            description="Cursor MCP CLI 또는 fastmcp CLI를 설치합니다.",
                            commands=[
                                MCPGuideCommand(text="npm i -g fastmcp-cli"),
                            ],
                        ),
                        MCPGuideStep(
                            title="2. 프로젝트 등록",
                            description="Cursor와 연동할 프로젝트를 등록합니다.",
                            commands=[
                                MCPGuideCommand(text="cd /path/to/project"),
                                MCPGuideCommand(text="fastmcp init --provider cursor --project <PROJECT_ID>"),
                            ],
                        ),
                        MCPGuideStep(
                            title="3. Cursor에서 실행",
                            description="태스크에서의 명령을 실행하거나 UI 버튼을 눌러주세요. 자연어 명령어도 지원합니다.",
                            commands=[
                                MCPGuideCommand(text='fastmcp run "프로젝트 <PROJECT_ID>의 다음 작업 진행"'),
                                MCPGuideCommand(text='fastmcp run "이번 sprint 요약해줘"'),
                            ],
                        ),
                    ],
                ),
                MCPGuidePlatform(
                    os="Windows",
                    steps=[
                        MCPGuideStep(
                            title="PowerShell에서 CLI 설치",
                            description="npm이 PATH에 있어야 합니다.",
                            commands=[
                                MCPGuideCommand(text="npm i -g fastmcp-cli"),
                                MCPGuideCommand(text="fastmcp login --base-url <FASTMCP_URL>"),
                            ],
                        ),
                        MCPGuideStep(
                            title="프로젝트 준비",
                            description="프로젝트 디렉토리로 이동 후 MCP 구성을 생성합니다.",
                            commands=[
                                MCPGuideCommand(text="cd C:\\path\\to\\project"),
                                MCPGuideCommand(text="fastmcp init --provider cursor --project <PROJECT_ID>"),
                            ],
                        ),
                        MCPGuideStep(
                            title="Cursor에서 연결 확인",
                            description="태스크에서의 명령을 실행하거나 UI 버튼을 눌러주세요. 자연어 명령어도 지원합니다.",
                            commands=[
                                MCPGuideCommand(text='fastmcp run "프로젝트 <PROJECT_ID>의 다음 작업 진행"'),
                                MCPGuideCommand(text='fastmcp run "이번 sprint 요약해줘"'),
                            ],
                        ),
                    ],
                ),
            ],
        ),
    }

    def get_guide(self, provider_id: str) -> MCPGuideResponse:
        """에이전트 연동 가이드 조회."""
        guide = self._GUIDES.get(provider_id)
        if not guide:
            raise NotFoundError("MCPGuide", provider_id)
        return guide

    # ------------------------------------------------------------------
    # Copy-Paste Ready Config (vooster.ai style)
    # ------------------------------------------------------------------

    def generate_mcp_config_file(
        self, project_id: int, provider_id: str, api_token: str, user_os: str = "macOS"
    ) -> MCPConfigFileResponse:
        """MCP 설정 파일 (mcp.json) 생성 - 사용자가 복사-붙여넣기만 하면 됨."""
        project = self._get_project(project_id)

        # 연결이 없으면 생성
        connection = (
            self.db.query(models.MCPConnection)
            .filter(
                models.MCPConnection.project_id == project_id,
                models.MCPConnection.connection_type == provider_id,
            )
            .first()
        )

        if not connection:
            connection_data = self.create_connection(
                MCPConnectionCreate(provider_id=provider_id, project_id=str(project_id))
            )
            connection_id = connection_data.connection_id
            self.activate_connection(connection_id)
        else:
            connection_id = self._encode_id("cn", connection.id)
            if connection.status != "active":
                self.activate_connection(connection_id)

        # 백엔드 URL (환경 변수 또는 기본값)
        backend_url = settings.BACKEND_BASE_URL or "http://localhost:8000"

        # 프로젝트 루트 경로 (사용자가 수정해야 함 - 플레이스홀더 사용)
        # 실제 배포 시에는 사용자가 프로젝트 루트 경로로 교체해야 함
        project_root_placeholder = "/path/to/Efficient-AI-based-Development-BE"
        adapter_path = f"{project_root_placeholder}/mcp_adapter/server.py"
        python_path = f"{project_root_placeholder}/.venv/bin/python3"

        # OS별 설정 파일 경로
        if user_os.lower() == "windows":
            install_path = "%APPDATA%\\Cursor\\User\\globalStorage\\mcp.json"
            python_path = python_path.replace("/", "\\")
            adapter_path = adapter_path.replace("/", "\\")
        else:  # macOS, Linux
            install_path = "~/Library/Application Support/Cursor/User/globalStorage/mcp.json"

        # mcp.json 파일 내용 생성
        mcp_config = {
            "mcpServers": {
                "atlas-ai": {
                    "command": python_path,
                    "args": [adapter_path],
                    "env": {
                        "BACKEND_URL": backend_url,
                        "API_TOKEN": api_token,
                        "PROJECT_ID": str(project_id),
                        "CONNECTION_ID": connection_id,
                    },
                }
            }
        }

        config_content = json.dumps(mcp_config, indent=2, ensure_ascii=False)

        # 설정 방법 안내 (더 친화적으로)
        instructions = [
            "1. 아래 설정 파일 내용을 전체 복사하세요",
            f"2. {install_path} 파일을 열거나 생성하세요",
            "3. 복사한 내용을 붙여넣고 저장하세요",
            "4. ⚠️ 중요: Cursor를 완전히 종료하고 다시 시작하세요",
            "5. Cursor에서 MCP 연결이 활성화되었는지 확인하세요",
            "",
            "💡 팁: 프로젝트 루트 경로(/path/to/Efficient-AI-based-Development-BE)를 실제 경로로 수정해야 합니다.",
        ]

        return MCPConfigFileResponse(
            config_content=config_content,
            file_name="mcp.json",
            install_path=install_path,
            instructions=instructions,
        )

    def generate_task_command(
        self, task_id: int, provider_id: str = "cursor", command_format: str = "vooster"
    ) -> MCPTaskCommandResponse:
        """태스크별 MCP 명령어 생성 - Cursor에서 복사-붙여넣기만 하면 됨.
        
        Args:
            task_id: 태스크 ID
            provider_id: MCP 제공자 (cursor/claude/chatgpt)
            command_format: 명령어 형식 ("vooster" 또는 "natural")
                - "vooster": 구조화된 명령어 (예: "atlas-ai를 사용해서 프로젝트 148의 태스크 236 작업 수행하라")
                - "natural": 자연어 명령어 (예: "AI 기반 효율적 개발 플랫폼의 MCP Quick Test 구현해줘")
        """
        task = (
            self.db.query(models.Task)
            .filter(models.Task.id == task_id)
            .first()
        )
        if not task:
            raise NotFoundError("Task", str(task_id))

        # 프로젝트 정보 가져오기
        project = (
            self.db.query(models.Project)
            .filter(models.Project.id == task.project_id)
            .first()
        )

        # 명령어 형식에 따라 생성
        if command_format == "vooster":
            # Vooster.ai 스타일: 구조화된 명령어
            project_name = project.title if project else f"프로젝트 {task.project_id}"
            command = f"atlas-ai를 사용해서 {project_name}의 태스크 {task_id} 작업 수행하라"
            
            description = (
                f"위 명령어를 Cursor의 MCP 채팅창에 붙여넣으세요.\n"
                f"시스템이 자동으로 다음 정보를 수집하여 코드를 생성합니다:\n"
                f"- 프로젝트: {project_name}\n"
                f"- 태스크 ID: {task_id}\n"
                f"- 태스크 제목: {task.title}\n"
                f"- PRD/SRS/USER_STORY 문서\n"
                f"- 프로젝트 컨텍스트"
            )
        else:
            # 자연어 스타일 (기본값)
            if task.description_md:
                # description_md가 있으면 더 구체적인 명령어
                command = f"{task.title} 구현해줘. {task.description_md[:100]}..."
            else:
                command = f"{task.title} 구현해줘"

            # 프로젝트 정보 포함
            if project:
                project_name = project.title[:20] if project.title else f"프로젝트 {task.project_id}"
                command = f"{project_name}의 {command}"

            description = (
                f"위 명령어를 Cursor의 MCP 채팅창에 붙여넣으세요.\n"
                f"시스템이 자동으로 다음 정보를 수집하여 코드를 생성합니다:\n"
                f"- 태스크 정보: {task.title}\n"
                f"- PRD/SRS/USER_STORY 문서\n"
                f"- 프로젝트 컨텍스트"
            )

        return MCPTaskCommandResponse(
            command=command,
            task_id=task_id,
            task_title=task.title,
            description=description,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_project(self, project_id: int) -> models.Project:
        project = self.db.query(models.Project).filter(models.Project.id == project_id).first()
        if not project:
            raise NotFoundError("Project", str(project_id))
        return project

    def _get_connection(self, connection_id: int) -> models.MCPConnection:
        connection = self.db.query(models.MCPConnection).filter(models.MCPConnection.id == connection_id).first()
        if not connection:
            raise NotFoundError("MCPConnection", str(connection_id))
        return connection

    def _get_session(self, session_id: int) -> models.MCPSession:
        session = self.db.query(models.MCPSession).filter(models.MCPSession.id == session_id).first()
        if not session:
            raise NotFoundError("MCPSession", str(session_id))
        return session

    def _get_run(self, run_id: int) -> models.MCPRun:
        run = self.db.query(models.MCPRun).filter(models.MCPRun.id == run_id).first()
        if not run:
            raise NotFoundError("MCPRun", str(run_id))
        return run

    def _dump_json(self, payload: Any | None) -> str | None:
        if payload is None:
            return None
        return json.dumps(payload, ensure_ascii=False)

    def _load_json(self, payload: str | None) -> Any | None:
        if not payload:
            return None
        try:
            return json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValidationError(f"JSON 파싱에 실패했습니다: {exc}") from exc

    def _to_connection_data(self, connection: models.MCPConnection) -> MCPConnectionData:
        return MCPConnectionData(
            connection_id=self._encode_id("cn", connection.id),
            provider_id=connection.connection_type,
            status=self._map_connection_status(connection.status),
            created_at=connection.created_at,
            config=self._load_json(connection.config),
        )

    def _to_session_data(self, session: models.MCPSession) -> MCPSessionData:
        return MCPSessionData(
            session_id=self._encode_id("ss", session.id),
            connection_id=self._encode_id("cn", session.connection_id),
            project_id=str(session.project_id),
            status=session.status,
            created_at=session.created_at,
            metadata=self._load_json(session.metadata_json),
        )

    def _to_run_data(self, run: models.MCPRun) -> MCPRunData:
        return MCPRunData(
            run_id=self._encode_id("run", run.id),
            session_id=self._encode_id("ss", run.session_id),
            task_id=run.task_id,
            mode=run.mode,
            status=self._map_run_status(run.status),
            created_at=run.created_at,
            updated_at=run.updated_at,
            result=self._normalize_result(run.result),
        )

    def _to_run_status_data(self, run: models.MCPRun) -> MCPRunStatusData:
        result_payload = self._normalize_result(run.result)
        output_payload = (
            {"outputText": result_payload.get("outputText") or result_payload.get("output_text")}
            if isinstance(result_payload, dict)
            else None
        )
        return MCPRunStatusData(
            run_id=self._encode_id("run", run.id),
            task_id=run.task_id,
            status=self._map_run_status(run.status),
            result=result_payload if isinstance(result_payload, dict) else None,
            message=run.message,
            output=output_payload,
            started_at=run.created_at,
            finished_at=run.updated_at,
        )

    def _normalize_result(self, payload: str | None) -> dict[str, Any]:
        data = self._load_json(payload)
        if isinstance(data, dict):
            return data
        if data is None:
            return {}
        return {"value": data}

    def _execute_run(
        self,
        session: models.MCPSession,
        run: models.MCPRun,
        payload: MCPRunCreate,
    ) -> None:
        """실제 MCP 실행을 수행."""
        run.status = "running"
        run.progress = "0.5"
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)

        connection = session.connection
        provider_type = connection.connection_type
        mode = payload.mode or "chat"

        # Tool 모드는 실제 tool 실행 로직으로 처리
        if mode == "tool" and payload.tool_id:
            try:
                result_payload = self._execute_tool(
                    tool_id=payload.tool_id,
                    input_data=payload.input or {},
                    session=session,
                    provider_type=provider_type,
                )
                run.result = self._dump_json(result_payload)
                run.status = "succeeded"
                run.message = f"Tool '{payload.tool_id}' 실행이 완료되었습니다."
            except Exception as exc:
                run.result = self._dump_json({"error": str(exc)})
                run.status = "failed"
                run.message = f"Tool 실행 실패: {str(exc)}"
        elif provider_type == "chatgpt":
            if not settings.fastmcp_base_url or not settings.fastmcp_token:
                raise ValidationError("ChatGPT 실행을 위해 FASTMCP_BASE_URL과 FASTMCP_TOKEN 환경 변수를 설정하세요.")
            provider = ChatGPTProvider(
                base_url=settings.fastmcp_base_url,
                token=settings.fastmcp_token,
                model=settings.openai_model,
            )
            provider_arguments = self._build_chat_arguments(payload)
            result_payload = provider.run(provider_arguments)
            run.result = self._dump_json(result_payload)
            run.status = "succeeded"
            run.message = "ChatGPT 응답이 fastMCP를 통해 생성되었습니다."
        elif provider_type == "claude":
            if not settings.fastmcp_base_url or not settings.fastmcp_token:
                raise ValidationError("Claude 실행을 위해 FASTMCP_BASE_URL과 FASTMCP_TOKEN 환경 변수를 설정하세요.")
            provider = ClaudeProvider(
                base_url=settings.fastmcp_base_url,
                token=settings.fastmcp_token,
                model=settings.anthropic_model,
            )
            provider_arguments = self._build_chat_arguments(payload)
            result_payload = provider.run(provider_arguments)
            run.result = self._dump_json(result_payload)
            run.status = "succeeded"
            run.message = "Claude 응답이 fastMCP를 통해 생성되었습니다."
        elif provider_type == "cursor":
            if not settings.fastmcp_base_url or not settings.fastmcp_token:
                raise ValidationError("Cursor 실행을 위해 FASTMCP_BASE_URL과 FASTMCP_TOKEN 환경 변수를 설정하세요.")
            # Cursor는 OpenAI 기반이므로 기본 모델 사용
            provider = CursorProvider(
                base_url=settings.fastmcp_base_url,
                token=settings.fastmcp_token,
                model=settings.openai_model,
            )
            provider_arguments = self._build_chat_arguments(payload)
            result_payload = provider.run(provider_arguments)
            run.result = self._dump_json(result_payload)
            run.status = "succeeded"
            run.message = "Cursor 응답이 fastMCP를 통해 생성되었습니다."
        else:
            run.result = self._dump_json(
                {
                    "message": f"{provider_type} 실행은 아직 지원되지 않습니다.",
                }
            )
            run.status = "succeeded"
            run.message = "외부 MCP 실행은 아직 구현되지 않았습니다."

        run.progress = "1.0"
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)

    def _build_chat_arguments(self, payload: MCPRunCreate) -> dict[str, Any]:
        config = payload.config or {}
        arguments: dict[str, Any] = {}
        if config.get("model"):
            arguments["model"] = config["model"]
        if config.get("temperature") is not None:
            arguments["temperature"] = config["temperature"]
        if config.get("maxTokens") is not None:
            arguments["maxTokens"] = config["maxTokens"]

        mode = payload.mode or "chat"
        if mode == "chat":
            messages = payload.input.get("messages")
            if not isinstance(messages, list) or not messages:
                raise ValidationError("chat 모드 실행에는 messages 배열이 필요합니다.")
            system_prompt = config.get("systemPrompt")
            if system_prompt:
                messages = [{"role": "system", "content": system_prompt}, *messages]
            arguments["messages"] = messages
        elif mode == "tool":
            # Tool 모드는 실제 tool 실행 로직으로 처리
            arguments["prompt"] = self._format_tool_prompt(payload.tool_id, payload.input)
        elif mode == "prompt":
            arguments["prompt"] = self._format_prompt_payload(payload.prompt_id, payload.input)
        else:
            raise ValidationError("지원하지 않는 실행 모드입니다.")

        return arguments

    def _execute_tool(
        self,
        tool_id: str,
        input_data: dict[str, Any],
        session: models.MCPSession,
        provider_type: str,
    ) -> dict[str, Any]:
        """실제 tool 실행 로직."""
        project_id = session.connection.project_id

        if tool_id == "start_development":
            return self._execute_start_development(input_data, session)
        elif tool_id == "generate_code":
            return self._execute_generate_code(input_data, session, project_id)
        elif tool_id == "review_code":
            return self._execute_review_code(input_data, session, project_id)
        elif tool_id == "sync_tasks":
            return self._execute_sync_tasks(input_data, project_id)
        else:
            raise ValidationError(f"알 수 없는 tool: {tool_id}")

    def _execute_start_development(self, input_data: dict[str, Any], session: models.MCPSession) -> dict[str, Any]:
        """Start Development tool 실행."""
        from app.domain.tasks import start_development_service

        task_id = input_data.get("taskId")
        if not isinstance(task_id, int):
            raise ValidationError("start_development tool에는 taskId(int)가 필요합니다.")

        task = (
            self.db.query(models.Task)
            .filter(models.Task.id == task_id)
            .first()
        )
        if not task:
            raise ValidationError(f"태스크를 찾을 수 없습니다: {task_id}")

        if task.project_id != session.connection.project_id:
            raise ValidationError("현재 세션과 동일한 프로젝트의 태스크만 실행할 수 있습니다.")

        provider_id = input_data.get("providerId") or session.connection.connection_type
        options = input_data.get("options")

        request = StartDevelopmentRequest(provider_id=provider_id, options=options)
        result = start_development_service(task_id, request, self.db)

        return {
            "taskId": task_id,
            "sessionId": result.session_id,
            "runId": result.run_id,
            "status": result.status,
            "preview": result.preview,
            "summary": result.summary,
            "providerId": provider_id,
        }

    def _collect_task_context(self, task_id: int) -> dict[str, Any]:
        """태스크와 관련 문서 정보를 수집합니다."""
        task = (
            self.db.query(models.Task)
            .filter(models.Task.id == task_id)
            .first()
        )
        if not task:
            raise ValidationError(f"태스크를 찾을 수 없습니다: {task_id}")

        project = (
            self.db.query(models.Project)
            .filter(models.Project.id == task.project_id)
            .first()
        )
        if not project:
            raise ValidationError(f"프로젝트를 찾을 수 없습니다: {task.project_id}")

        documents = (
            self.db.query(models.Document)
            .filter(models.Document.project_id == project.id)
            .order_by(models.Document.updated_at.desc())
            .all()
        )

        prd_doc = next((doc for doc in documents if doc.type == "PRD"), None)
        srs_doc = next((doc for doc in documents if doc.type == "SRS"), None)
        user_story_docs = [doc for doc in documents if doc.type == "USER_STORY"]

        return {
            "task": task,
            "project": project,
            "prd_doc": prd_doc,
            "srs_doc": srs_doc,
            "user_story_docs": user_story_docs,
            "documents": documents,
        }

    def _execute_generate_code(self, input_data: dict[str, Any], session: models.MCPSession, project_id: int) -> dict[str, Any]:
        """코드 생성 tool 실행 - 태스크와 문서 정보를 활용."""
        task_id = input_data.get("taskId")
        if not isinstance(task_id, int):
            raise ValidationError("generate_code tool에는 taskId(int)가 필요합니다.")

        task = (
            self.db.query(models.Task)
            .filter(models.Task.id == task_id)
            .first()
        )
        if not task:
            raise ValidationError(f"태스크를 찾을 수 없습니다: {task_id}")

        if task.project_id != project_id:
            raise ValidationError("현재 세션과 동일한 프로젝트의 태스크만 실행할 수 있습니다.")

        # 태스크와 문서 정보 수집
        context = self._collect_task_context(task_id)
        
        # 파일 경로 (선택)
        file_path = input_data.get("filePath")
        options = input_data.get("options", {})

        # 코드 생성 프롬프트 구성
        # 태스크 정보를 명확하게 강조
        prompt_parts = [
            "=" * 60,
            f"# ⚠️ 중요: 다음 태스크를 정확히 구현하세요",
            "=" * 60,
            "",
            f"## 태스크 제목: {task.title}",
            f"## 태스크 ID: {task_id}",
            "",
            "## 태스크 상세 요구사항",
            task.description_md or task.description or "No description",
            "",
            "=" * 60,
            "",
        ]

        if context.get("prd_doc") and context["prd_doc"].content_md:
            prompt_parts.extend([
                "## PRD 문서",
                context["prd_doc"].content_md[:1000],  # 일부만 포함
                "",
            ])

        if context.get("srs_doc") and context["srs_doc"].content_md:
            prompt_parts.extend([
                "## SRS 문서",
                context["srs_doc"].content_md[:1000],
                "",
            ])

        # USER_STORY 문서들도 포함
        user_story_docs = context.get("user_story_docs", [])
        if user_story_docs:
            prompt_parts.extend([
                "## USER_STORY 문서",
            ])
            for us_doc in user_story_docs[:3]:  # 최대 3개만 포함
                if us_doc.content_md:
                    prompt_parts.extend([
                        f"### {us_doc.title}",
                        us_doc.content_md[:500],  # 각 스토리 500자 제한
                        "",
                    ])

        if file_path:
            prompt_parts.extend([
                f"## 생성할 파일",
                f"경로: {file_path}",
                "",
            ])

        prompt = "\n".join(prompt_parts)

        # 수집된 정보를 요약하여 즉시 반환
        # 실제 코드 생성은 Cursor AI가 프롬프트를 받아서 수행
        
        # 수집된 정보 요약
        summary_parts = [
            f"✅ 태스크 정보 수집 완료: {task.title}",
            f"✅ 프로젝트: {context['project'].title}",
        ]
        
        if context.get("prd_doc"):
            summary_parts.append(f"✅ PRD 문서: {context['prd_doc'].title} ({len(context['prd_doc'].content_md or '')} 문자)")
        else:
            summary_parts.append("⚠️ PRD 문서: 없음")
        
        if context.get("srs_doc"):
            summary_parts.append(f"✅ SRS 문서: {context['srs_doc'].title} ({len(context['srs_doc'].content_md or '')} 문자)")
        else:
            summary_parts.append("⚠️ SRS 문서: 없음")
        
        user_story_count = len(context.get("user_story_docs", []))
        if user_story_count > 0:
            summary_parts.append(f"✅ USER_STORY 문서: {user_story_count}개")
            for us_doc in context["user_story_docs"][:3]:
                summary_parts.append(f"   - {us_doc.title}")
        else:
            summary_parts.append("⚠️ USER_STORY 문서: 없음")
        
        summary = "\n".join(summary_parts)
        
        # 프롬프트를 결과에 포함하여 Cursor가 사용할 수 있도록
        # Cursor가 바로 사용할 수 있도록 더 명확한 형식으로 구성
        result_data = {
            "code": prompt,  # 전체 프롬프트를 코드로 반환 (Cursor가 이를 기반으로 코드 생성)
            "filePath": file_path,
            "summary": summary,
            "message": "태스크 정보와 문서가 수집되었습니다. 위 프롬프트를 기반으로 코드를 생성하세요.",
            "collectedContext": {
                "taskId": task_id,
                "taskTitle": task.title,
                "projectTitle": context["project"].title,
                "hasPRD": context.get("prd_doc") is not None,
                "hasSRS": context.get("srs_doc") is not None,
                "userStoryCount": user_story_count,
            },
            # Cursor가 바로 사용할 수 있도록 추가 정보
            "taskInfo": {
                "id": task_id,
                "title": task.title,
                "description": task.description_md or task.description or "",
            },
            "projectInfo": {
                "id": context["project"].id,
                "title": context["project"].title,
            },
        }

        return result_data

    def _execute_review_code(self, input_data: dict[str, Any], session: models.MCPSession, project_id: int) -> dict[str, Any]:
        """코드 리뷰 tool 실행 - 태스크 요구사항과 문서를 기준으로 검토."""
        task_id = input_data.get("taskId")
        if not isinstance(task_id, int):
            raise ValidationError("review_code tool에는 taskId(int)가 필요합니다.")

        task = (
            self.db.query(models.Task)
            .filter(models.Task.id == task_id)
            .first()
        )
        if not task:
            raise ValidationError(f"태스크를 찾을 수 없습니다: {task_id}")

        if task.project_id != project_id:
            raise ValidationError("현재 세션과 동일한 프로젝트의 태스크만 실행할 수 있습니다.")

        # 태스크와 문서 정보 수집
        context = self._collect_task_context(task_id)
        
        file_paths = input_data.get("filePaths", [])

        # 코드 리뷰 프롬프트 구성
        prompt_parts = [
            f"# 코드 리뷰 요청: {task.title}",
            "",
            "## 태스크 요구사항",
            task.description_md or task.description or "No description",
            "",
        ]

        if context.get("prd_doc") and context["prd_doc"].content_md:
            prompt_parts.extend([
                "## PRD 기준",
                context["prd_doc"].content_md[:1000],
                "",
            ])

        if context.get("srs_doc") and context["srs_doc"].content_md:
            prompt_parts.extend([
                "## SRS 기준",
                context["srs_doc"].content_md[:1000],
                "",
            ])

        # USER_STORY 문서들도 포함
        user_story_docs = context.get("user_story_docs", [])
        if user_story_docs:
            prompt_parts.extend([
                "## USER_STORY 기준",
            ])
            for us_doc in user_story_docs[:3]:  # 최대 3개만 포함
                if us_doc.content_md:
                    prompt_parts.extend([
                        f"### {us_doc.title}",
                        us_doc.content_md[:500],  # 각 스토리 500자 제한
                        "",
                    ])

        if file_paths:
            prompt_parts.extend([
                "## 리뷰할 파일",
                "\n".join(f"- {fp}" for fp in file_paths),
                "",
            ])

        prompt_parts.extend([
            "위 태스크와 문서를 기준으로 코드를 리뷰하고, 개선 사항과 이슈를 제안해주세요.",
        ])

        prompt = "\n".join(prompt_parts)

        # MCP Run 생성하여 코드 리뷰 실행
        run_data = self.create_run(
            MCPRunCreate(
                session_id=session.id,
                mode="chat",
                task_id=task_id,
                input={
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a code review assistant. Review code against requirements and suggest improvements.",
                        },
                        {"role": "user", "content": prompt},
                    ]
                },
                config={
                    "temperature": 0.3,
                },
            )
        )

        # 결과 파싱 (실제 구현 시 구조화된 파싱 필요)
        result_text = str(run_data.result) if run_data.result else ""
        issues = []
        suggestions = []

        # 간단한 파싱 (실제로는 더 정교한 파싱 필요)
        if "이슈" in result_text or "issue" in result_text.lower():
            issues.append({"type": "general", "message": result_text[:200]})
        if "제안" in result_text or "suggestion" in result_text.lower():
            suggestions.append(result_text[:200])

        return {
            "taskId": task_id,
            "reviewedFiles": file_paths if file_paths else ["all"],
            "issues": issues,
            "suggestions": suggestions,
            "status": run_data.status,
        }

    def _execute_sync_tasks(self, input_data: dict[str, Any], project_id: int) -> dict[str, Any]:
        """태스크 동기화 tool 실행."""
        tasks = (
            self.db.query(models.Task)
            .filter(models.Task.project_id == project_id)
            .order_by(models.Task.updated_at.desc())
            .all()
        )

        task_list = []
        for task in tasks:
            task_list.append({
                "id": task.id,
                "title": task.title,
                "status": task.status,
                "type": task.type,
                "priority": task.priority,
                "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            })

        return {
            "synced": True,
            "task_count": len(task_list),
            "tasks": task_list,
        }


    def _format_tool_prompt(
        self,
        tool_id: str | None,
        input_payload: dict[str, Any],
    ) -> str:
        prefix = f"[Tool: {tool_id or 'tool'}]\n"
        return prefix + json.dumps(input_payload, ensure_ascii=False, indent=2)

    def _format_prompt_payload(
        self,
        prompt_id: str | None,
        input_payload: dict[str, Any],
    ) -> str:
        prefix = f"[Prompt: {prompt_id or 'prompt'}]\n"
        return prefix + json.dumps(input_payload, ensure_ascii=False, indent=2)

    def _encode_id(self, prefix: str, value: int) -> str:
        return f"{prefix}_{value:04d}"

    def _decode_connection_id(self, external_id: str, prefix: str) -> int:
        candidate = external_id
        token = f"{prefix}_"
        if external_id.startswith(token):
            candidate = external_id[len(token) :]
        try:
            return int(candidate)
        except ValueError as exc:
            raise ValidationError(f"유효하지 않은 ID 형식입니다: {external_id}") from exc

    def _parse_project_identifier(self, identifier: str) -> int:
        try:
            return int(identifier)
        except ValueError:
            digits = "".join(ch for ch in identifier if ch.isdigit())
            if digits:
                return int(digits)
        raise ValidationError("프로젝트 ID는 숫자여야 합니다.")

    def _map_connection_status(self, status: str) -> str:
        mapping = {
            "pending": "pending",
            "active": "connected",
            "connected": "connected",
            "inactive": "disconnected",
            "error": "error",
        }
        return mapping.get(status, status)

    def _map_run_status(self, status: str) -> str:
        mapping = {
            "pending": "queued",
            "running": "running",
            "completed": "succeeded",
            "succeeded": "succeeded",
            "failed": "failed",
            "cancelled": "cancelled",
        }
        return mapping.get(status, status)

    def _resolve_project_status(self, connections: list[models.MCPConnection]) -> str | None:
        if not connections:
            return None

        if any(conn.status in {"connected", "active"} for conn in connections):
            return "connected"

        if any(conn.status == "pending" for conn in connections):
            return "pending"

        if any(conn.status == "error" for conn in connections):
            return "pending"

        return None
