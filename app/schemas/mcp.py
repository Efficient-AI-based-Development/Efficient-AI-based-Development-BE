"""MCP (Model Context Protocol) related Pydantic schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------


class MCPConnectionCreate(BaseModel):
    provider_id: str = Field(
        ...,
        alias="providerId",
        description="연결 대상 MCP 제공자 식별자",
        examples=["chatgpt", "claude", "cursor"],
    )
    project_id: str = Field(
        ...,
        alias="projectId",
        description="프로젝트 ID(프론트에서는 문자열로 전달)",
        examples=["41", "proj-23"],
    )
    config: dict[str, Any] | None = Field(
        default=None,
        description="연결별 기본 설정(JSON). 예: 모델명, 기본 온도값 등",
        examples=[{"model": "gpt-4o-mini", "temperature": 0.2}],
    )
    env: dict[str, Any] | None = Field(
        default=None,
        description="연결 시 필요한 환경 변수(JSON). API 키 등 민감정보는 서버/시크릿에서 관리 권장",
        examples=[{"OPENAI_API_KEY": "sk-***"}],
    )

    model_config = ConfigDict(populate_by_name=True)


class MCPConnectionData(BaseModel):
    connection_id: str = Field(
        ...,
        alias="connectionId",
        description="외부 노출용 연결 ID (cn_0001 형태)",
        examples=["cn_0007"],
    )
    provider_id: str = Field(
        ...,
        alias="providerId",
        description="연결된 MCP 제공자 ID",
        examples=["chatgpt", "claude"],
    )
    status: str = Field(
        ...,
        description="연결 상태. pending/active/inactive/error 중 하나",
        examples=["pending", "active"],
    )
    created_at: datetime = Field(
        ...,
        alias="createdAt",
        description="연결 생성 시각 (UTC)",
    )
    config: dict[str, Any] | None = Field(
        default=None,
        description="저장된 기본 설정(JSON)",
    )

    model_config = ConfigDict(populate_by_name=True)


class MCPConnectionResponse(BaseModel):
    data: MCPConnectionData


class MCPConnectionListResponse(BaseModel):
    data: list[MCPConnectionData]


class MCPConnectionCloseResponse(BaseModel):
    data: dict[str, Any]


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------


class MCPSessionCreate(BaseModel):
    connection_id: str = Field(
        ...,
        alias="connectionId",
        description="세션을 생성할 연결 ID",
        examples=["cn_0007"],
    )
    project_id: str = Field(
        ...,
        alias="projectId",
        description="프로젝트 ID",
        examples=["41"],
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="프론트에서 세션에 부여하고 싶은 메타데이터",
        examples=[{"tabId": "session-tab-1"}],
    )

    model_config = ConfigDict(populate_by_name=True)


class MCPSessionData(BaseModel):
    session_id: str = Field(
        ...,
        alias="sessionId",
        description="외부 노출용 세션 ID (ss_0001 형태)",
        examples=["ss_0003"],
    )
    connection_id: str = Field(
        ...,
        alias="connectionId",
        description="세션이 속하는 연결 ID",
        examples=["cn_0007"],
    )
    status: str = Field(
        ...,
        description="세션 상태. ready/active/closed/error 등",
        examples=["ready"],
    )
    created_at: datetime = Field(
        ...,
        alias="createdAt",
        description="세션 생성 시각 (UTC)",
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="저장된 세션 메타데이터(JSON)",
    )

    model_config = ConfigDict(populate_by_name=True)


class MCPSessionResponse(BaseModel):
    data: MCPSessionData


class MCPSessionListResponse(BaseModel):
    data: list[MCPSessionData]


class MCPSessionCloseResponse(BaseModel):
    data: dict[str, Any]


# ---------------------------------------------------------------------------
# Catalog (Tools / Resources / Prompts)
# ---------------------------------------------------------------------------


class MCPToolItem(BaseModel):
    tool_id: str = Field(
        ...,
        alias="toolId",
        description="툴 ID",
        examples=["gen_user_story"],
    )
    name: str = Field(
        ...,
        description="툴 표시 이름",
        examples=["User Story Generator"],
    )
    description: str | None = Field(
        default=None,
        description="툴 동작에 대한 설명",
    )
    input_schema: dict[str, Any] | None = Field(
        default=None,
        alias="inputSchema",
        description="툴 호출 시 입력 JSON 스키마",
    )
    output_schema: dict[str, Any] | None = Field(
        default=None,
        alias="outputSchema",
        description="툴 실행 결과 JSON 스키마",
    )

    model_config = ConfigDict(populate_by_name=True)


class MCPToolListResponse(BaseModel):
    data: list[MCPToolItem]


class MCPResourceItem(BaseModel):
    uri: str = Field(
        ...,
        description="리소스 URI (file://, search:// 등)",
        examples=["file:///app/README.md"],
    )
    kind: str = Field(
        ...,
        description="리소스 유형 또는 소스",
        examples=["file", "search"],
    )
    description: str | None = Field(
        default=None,
        description="리소스 설명",
    )


class MCPResourceListResponse(BaseModel):
    data: list[MCPResourceItem]


class MCPPromptItem(BaseModel):
    prompt_id: str = Field(
        ...,
        alias="promptId",
        description="프롬프트 ID",
        examples=["fix_tests"],
    )
    name: str = Field(
        ...,
        description="프롬프트 이름",
        examples=["Fix failing tests"],
    )
    description: str | None = Field(
        default=None,
        description="프롬프트 설명 및 활용법",
    )

    model_config = ConfigDict(populate_by_name=True)


class MCPPromptListResponse(BaseModel):
    data: list[MCPPromptItem]


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------


class MCPRunCreate(BaseModel):
    session_id: str = Field(
        ...,
        alias="sessionId",
        description="실행을 수행할 세션 ID",
        examples=["ss_0003"],
    )
    mode: str = Field(
        "chat",
        description="실행 모드. chat/tool/prompt 중 하나",
        examples=["chat", "tool"],
    )
    tool_id: str | None = Field(
        default=None,
        alias="toolId",
        description="툴 실행 시 필요한 툴 ID",
        examples=["gen_user_story"],
    )
    prompt_id: str | None = Field(
        default=None,
        alias="promptId",
        description="프롬프트 실행 시 필요한 프롬프트 ID",
        examples=["fix_tests"],
    )
    config: dict[str, Any] | None = Field(
        default=None,
        description="실행 시점에 사용할 런타임 설정(JSON)",
        examples=[{"temperature": 0.2}],
    )
    input: dict[str, Any] = Field(
        ...,
        description="실행 입력 데이터(JSON). 모드에 따라 메시지, 파라미터 등 구조가 달라짐",
        examples=[{"messages": [{"role": "user", "content": "이번 sprint 요약해줘"}]}],
    )

    model_config = ConfigDict(populate_by_name=True)


class MCPRunData(BaseModel):
    run_id: str = Field(
        ...,
        alias="runId",
        description="실행 ID (run_0001 형태)",
        examples=["run_0010"],
    )
    session_id: str = Field(
        ...,
        alias="sessionId",
        description="실행이 속하는 세션 ID",
        examples=["ss_0003"],
    )
    mode: str | None = Field(
        default=None,
        description="실행 모드 (chat/tool/prompt)",
    )
    status: str = Field(
        ...,
        description="실행 상태. queued/running/succeeded/failed/cancelled 등",
        examples=["running", "succeeded"],
    )
    created_at: datetime = Field(
        ...,
        alias="createdAt",
        description="생성 시각 (UTC)",
    )
    updated_at: datetime = Field(
        ...,
        alias="updatedAt",
        description="마지막 상태 갱신 시각 (UTC)",
    )
    result: dict[str, Any] | None = Field(
        default=None,
        description="AI 실행 결과 원본(JSON)",
    )

    model_config = ConfigDict(populate_by_name=True)


class MCPRunResponse(BaseModel):
    data: MCPRunData


class MCPRunStatusData(BaseModel):
    run_id: str = Field(
        ...,
        alias="runId",
        description="실행 ID",
        examples=["run_0010"],
    )
    status: str = Field(
        ...,
        description="실행 상태",
        examples=["running", "succeeded", "failed"],
    )
    result: dict[str, Any] | None = Field(
        default=None,
        description="현재까지 수집된 결과(JSON)",
    )
    message: str | None = Field(
        default=None,
        description="상태 메시지나 오류 메시지",
        examples=["ChatGPT 응답이 생성되었습니다."],
    )
    output: dict[str, Any] | None = Field(
        default=None,
        description="프론트 사용을 위한 가공된 출력(JSON)",
        examples=[{"outputText": "요약..."}],
    )
    started_at: datetime | None = Field(
        default=None,
        alias="startedAt",
        description="실행 시작 시각 (UTC)",
    )
    finished_at: datetime | None = Field(
        default=None,
        alias="finishedAt",
        description="실행 종료 시각 (UTC)",
    )

    model_config = ConfigDict(populate_by_name=True)


class MCPRunStatusResponse(BaseModel):
    data: MCPRunStatusData


class MCPRunCancelResponse(BaseModel):
    data: dict[str, Any]


class MCPRunEventsResponse(BaseModel):
    data: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------


class MCPProjectStatusItem(BaseModel):
    id: str = Field(
        ...,
        description="프로젝트 ID",
        examples=["41"],
    )
    name: str = Field(
        ...,
        description="프로젝트 이름",
        examples=["테스트 프로젝트"],
    )
    mcp_status: str | None = Field(
        None,
        alias="mcpStatus",
        description="해당 프로젝트의 MCP 연결 상태. connected/pending/없음 등",
        examples=["connected", "pending", None],
    )

    model_config = ConfigDict(populate_by_name=True)


class MCPProjectStatusResponse(BaseModel):
    data: list[MCPProjectStatusItem]


# ---------------------------------------------------------------------------
# Provider Guide
# ---------------------------------------------------------------------------


class MCPGuideCommand(BaseModel):
    text: str = Field(..., description="터미널에 입력할 명령어", examples=["npm i -g fastmcp-cli"])


class MCPGuideStep(BaseModel):
    title: str = Field(..., description="단계 제목", examples=["1. MCP 서버 연결하기"])
    description: str | None = Field(
        default=None,
        description="단계 설명",
        examples=["터미널에서 한 번만 실행하면 됩니다."],
    )
    commands: list[MCPGuideCommand] = Field(
        default_factory=list,
        description="순서대로 실행할 명령어 목록",
    )


class MCPGuidePlatform(BaseModel):
    os: str = Field(..., description="운영체제 이름", examples=["macOS", "Windows"])
    steps: list[MCPGuideStep] = Field(..., description="운영체제별 안내 단계")


class MCPGuideResponse(BaseModel):
    provider_id: str = Field(
        ..., alias="providerId", description="MCP 제공자 ID", examples=["chatgpt"]
    )
    provider_name: str = Field(
        ...,
        alias="providerName",
        description="사용자에게 보여줄 제공자 이름",
        examples=["ChatGPT MCP"],
    )
    supported_agents: list[str] = Field(
        default_factory=list,
        alias="supportedAgents",
        description="연동 가능한 에이전트 목록",
        examples=[["Cursor", "Claude Code"]],
    )
    prerequisites: list[str] = Field(
        default_factory=list,
        description="사전 준비 사항",
        examples=[["Node.js 20 이상 설치"]],
    )
    platforms: list[MCPGuidePlatform] = Field(
        ...,
        description="운영체제별 단계 안내",
    )

    model_config = ConfigDict(populate_by_name=True)
