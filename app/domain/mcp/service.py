"""MCP (Model Context Protocol) 서비스 골격."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session  # type: ignore

from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError
from app.db import models
from app.domain.mcp.providers import ChatGPTProvider, ClaudeProvider

from app.schemas.mcp import (
    MCPConnectionCreate,
    MCPConnectionData,
    MCPProjectStatusItem,
    MCPRunCreate,
    MCPRunData,
    MCPRunStatusData,
    MCPToolItem,
    MCPResourceItem,
    MCPPromptItem,
    MCPSessionCreate,
    MCPSessionData,
    MCPGuideResponse,
    MCPGuidePlatform,
    MCPGuideStep,
    MCPGuideCommand,
)


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

    def list_connections(self, project_identifier: Optional[str] = None) -> List[MCPConnectionData]:
        """MCP 연결 목록 조회."""
        query = self.db.query(models.MCPConnection)
        if project_identifier is not None:
            project_id = self._parse_project_identifier(project_identifier)
            query = query.filter(models.MCPConnection.project_id == project_id)
        connections = query.order_by(models.MCPConnection.created_at.desc()).all()
        return [self._to_connection_data(conn) for conn in connections]

    def deactivate_connection(self, external_connection_id: str) -> Dict[str, Any]:
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
        connection_id = self._decode_connection_id(payload.connection_id, prefix="cn")
        connection = self._get_connection(connection_id)
        if connection.status not in {"connected", "active"}:
            raise ValidationError("활성화된 MCP 연결에서만 세션을 시작할 수 있습니다.")

        session = models.MCPSession(
            connection_id=connection.id,
            status="ready",
            context=self._dump_json({}),
            metadata_json=self._dump_json(payload.metadata),
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return self._to_session_data(session)

    def list_sessions(self, connection_identifier: Optional[str] = None) -> List[MCPSessionData]:
        """MCP 세션 목록 조회."""
        query = self.db.query(models.MCPSession)
        if connection_identifier is not None:
            connection_id = self._decode_connection_id(connection_identifier, prefix="cn")
            query = query.filter(models.MCPSession.connection_id == connection_id)
        sessions = query.order_by(models.MCPSession.created_at.desc()).all()
        return [self._to_session_data(session) for session in sessions]

    def close_session(self, external_session_id: str) -> Dict[str, Any]:
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
    _TOOL_REGISTRY: Dict[str, List[Dict[str, Any]]] = {
        "chatgpt": [
            {
                "toolId": "gen_user_story",
                "name": "User Story Generator",
                "description": "PRD 문서를 기반으로 사용자 스토리를 생성합니다.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "args": {
                            "type": "object",
                            "properties": {
                                "prdMd": {"type": "string", "description": "PRD Markdown"},
                            },
                        }
                    },
                },
                "outputSchema": {
                    "type": "object",
                    "properties": {
                        "stories": {
                            "type": "array",
                            "items": {"type": "string"},
                        }
                    },
                },
            }
        ],
        "cursor": [
            {
                "toolId": "sync_tasks",
                "name": "Sync Tasks",
                "description": "Cursor 프로젝트 태스크를 최신 상태로 동기화합니다.",
                "inputSchema": {"type": "object"},
                "outputSchema": {"type": "object"},
            }
        ],
        "claude": [
            {
                "toolId": "summarize_requirements",
                "name": "Requirement Summarizer",
                "description": "요구사항을 간단히 요약합니다.",
                "inputSchema": {"type": "object"},
                "outputSchema": {"type": "object"},
            }
        ],
    }

    _RESOURCE_REGISTRY: Dict[str, List[Dict[str, Any]]] = {
        "chatgpt": [
            {
                "uri": "file:///app/README.md",
                "kind": "file",
                "description": "프로젝트 README 파일",
            },
            {
                "uri": "search:///code?query=auth",
                "kind": "search",
                "description": "코드베이스 내 인증 관련 검색",
            },
        ],
        "cursor": [
            {
                "uri": "project://tasks",
                "kind": "tasks",
                "description": "Cursor 태스크 목록",
            }
        ],
        "claude": [
            {
                "uri": "knowledge://architecture",
                "kind": "document",
                "description": "시스템 아키텍처 문서",
            }
        ],
    }

    _PROMPT_REGISTRY: Dict[str, List[Dict[str, Any]]] = {
        "chatgpt": [
            {
                "promptId": "fix_tests",
                "name": "Fix failing tests",
                "description": "실패하는 테스트를 해결하기 위한 조언을 제공합니다.",
            }
        ],
        "cursor": [
            {
                "promptId": "implement_feature",
                "name": "Implement Feature Prompt",
                "description": "새로운 기능 구현을 위한 프롬프트",
            }
        ],
        "claude": [
            {
                "promptId": "brainstorm_ideas",
                "name": "Brainstorm Ideas",
                "description": "새로운 기능 아이디어 브레인스토밍",
            }
        ],
    }

    def list_tools(self, external_session_id: str) -> List[MCPToolItem]:
        """세션별 사용 가능한 MCP 툴 목록 조회."""
        session_id = self._decode_connection_id(external_session_id, prefix="ss")
        session = self._get_session(session_id)
        connection_type = session.connection.connection_type
        tools = self._TOOL_REGISTRY.get(connection_type, [])
        return [MCPToolItem(**tool) for tool in tools]

    def list_resources(self, external_session_id: str) -> List[MCPResourceItem]:
        """세션별 리소스 목록 조회."""
        session_id = self._decode_connection_id(external_session_id, prefix="ss")
        session = self._get_session(session_id)
        connection_type = session.connection.connection_type
        resources = self._RESOURCE_REGISTRY.get(connection_type, [])
        return [MCPResourceItem(**resource) for resource in resources]

    def list_prompts(self, external_session_id: str) -> List[MCPPromptItem]:
        """세션별 프롬프트 목록 조회."""
        session_id = self._decode_connection_id(external_session_id, prefix="ss")
        session = self._get_session(session_id)
        connection_type = session.connection.connection_type
        prompts = self._PROMPT_REGISTRY.get(connection_type, [])
        return [MCPPromptItem(**prompt) for prompt in prompts]

    # ------------------------------------------------------------------
    # Project status
    # ------------------------------------------------------------------
    def list_project_statuses(self) -> List[MCPProjectStatusItem]:
        """프로젝트별 MCP 상태 요약."""
        projects = self.db.query(models.Project).all()
        return [
            MCPProjectStatusItem(
                id=str(project.id),
                name=project.name,
                mcp_status=self._resolve_project_status(project.mcp_connections),
            )
            for project in projects
        ]

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

    def cancel_run(self, external_run_id: str) -> Dict[str, Any]:
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

    def list_run_events(self, external_run_id: str) -> List[Dict[str, Any]]:
        """MCP 실행 이벤트 목록."""
        run_id = self._decode_connection_id(external_run_id, prefix="run")
        run = self._get_run(run_id)
        result_payload = self._load_json(run.result)

        events: List[Dict[str, Any]] = [
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

    _GUIDES: Dict[str, MCPGuideResponse] = {
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
                            description="에이전트 터미널(예: Cursor 커맨드 팔레트)에서 아래 명령을 실행하면 작업을 진행할 수 있습니다.",
                            commands=[
                                MCPGuideCommand(text="fastmcp run --project <PROJECT_ID>"),
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
                            description="에이전트에서 아래 명령을 실행하거나 버튼을 눌러 작업을 시작합니다.",
                            commands=[
                                MCPGuideCommand(text="fastmcp run --project <PROJECT_ID>"),
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
                            description="Claude Code에서 MCP 프로젝트를 실행하면 연결됩니다.",
                            commands=[
                                MCPGuideCommand(text="fastmcp run --provider claude --project <PROJECT_ID>"),
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
                            description="명령어를 실행하거나 Claude Code에서 MCP 실행 버튼을 눌러주세요.",
                            commands=[
                                MCPGuideCommand(text="fastmcp run --provider claude --project <PROJECT_ID>"),
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
                            description="`Cmd+Shift+P` → `Open MCP Project` 후 아래 명령을 실행하거나 UI 버튼을 눌러주세요.",
                            commands=[
                                MCPGuideCommand(text="fastmcp run --provider cursor --project <PROJECT_ID>"),
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
                            description="Cursor Command Palette에서 MCP 프로젝트를 선택하면 연결됩니다.",
                            commands=[
                                MCPGuideCommand(text="fastmcp run --provider cursor --project <PROJECT_ID>"),
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
            status=session.status,
            created_at=session.created_at,
            metadata=self._load_json(session.metadata_json),
        )

    def _to_run_data(self, run: models.MCPRun) -> MCPRunData:
        return MCPRunData(
            run_id=self._encode_id("run", run.id),
            session_id=self._encode_id("ss", run.session_id),
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
            status=self._map_run_status(run.status),
            result=result_payload if isinstance(result_payload, dict) else None,
            message=run.message,
            output=output_payload,
            started_at=run.created_at,
            finished_at=run.updated_at,
        )

    def _normalize_result(self, payload: Optional[str]) -> Dict[str, Any]:
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

        if provider_type == "chatgpt":
            if not settings.fastmcp_base_url or not settings.fastmcp_token:
                raise ValidationError(
                    "ChatGPT 실행을 위해 FASTMCP_BASE_URL과 FASTMCP_TOKEN 환경 변수를 설정하세요."
                )
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
                raise ValidationError(
                    "Claude 실행을 위해 FASTMCP_BASE_URL과 FASTMCP_TOKEN 환경 변수를 설정하세요."
                )
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

    def _build_chat_arguments(self, payload: MCPRunCreate) -> Dict[str, Any]:
        config = payload.config or {}
        arguments: Dict[str, Any] = {}
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
            arguments["prompt"] = self._format_tool_prompt(payload.tool_id, payload.input)
        elif mode == "prompt":
            arguments["prompt"] = self._format_prompt_payload(payload.prompt_id, payload.input)
        else:
            raise ValidationError("지원하지 않는 실행 모드입니다.")

        return arguments

    def _format_tool_prompt(
        self,
        tool_id: Optional[str],
        input_payload: Dict[str, Any],
    ) -> str:
        prefix = f"[Tool: {tool_id or 'tool'}]\n"
        return prefix + json.dumps(input_payload, ensure_ascii=False, indent=2)

    def _format_prompt_payload(
        self,
        prompt_id: Optional[str],
        input_payload: Dict[str, Any],
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

    def _resolve_project_status(
        self, connections: List[models.MCPConnection]
    ) -> Optional[str]:
        if not connections:
            return None

        if any(conn.status in {"connected", "active"} for conn in connections):
            return "connected"

        if any(conn.status == "pending" for conn in connections):
            return "pending"

        if any(conn.status == "error" for conn in connections):
            return "pending"

        return None
