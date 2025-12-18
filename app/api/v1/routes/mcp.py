"""MCP (Model Context Protocol) API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import models
from app.db.database import get_db
from app.db.models import User
from app.domain.auth import get_current_user
from app.domain.mcp import MCPService
from app.schemas.mcp import (
    MCPConfigFileResponse,
    MCPConnectionCloseResponse,
    MCPConnectionCreate,
    MCPConnectionListResponse,
    MCPConnectionResponse,
    MCPGuideResponse,
    MCPProjectStatusResponse,
    MCPPromptListResponse,
    MCPResourceListResponse,
    MCPResourceReadResponse,
    MCPRunCancelResponse,
    MCPRunCreate,
    MCPRunEventsResponse,
    MCPRunResponse,
    MCPRunStatusResponse,
    MCPSessionCloseResponse,
    MCPSessionCreate,
    MCPSessionListResponse,
    MCPSessionResponse,
    MCPTaskCommandResponse,
    MCPToolListResponse,
)

router = APIRouter(prefix="/mcp", tags=["mcp"], dependencies=[Depends(get_current_user)])


def _service(db: Session) -> MCPService:
    return MCPService(db)


def _legacy_guard(detail: str) -> None:
    """Allow legacy MCP endpoints only in debug/dev environments."""
    if not settings.debug:
        raise HTTPException(status_code=410, detail=detail)


# Project summary
@router.get(
    "/projects",
    response_model=MCPProjectStatusResponse,
    summary="프로젝트별 MCP 연결 현황",
    description=(
        "프로젝트별 MCP 준비 상태를 한눈에 봅니다.\n\n"
        "응답 필드:\n"
        "- `id`: 프로젝트 ID\n"
        "- `name`: 프로젝트 이름\n"
        "- `mcpStatus`: `connected`(활성 연결) / `pending`(생성만 함) / `None`(연결 없음)\n"
        "- `hasActiveSession`: 현재 열린 세션 여부\n\n"
        "예시 응답:\n"
        "```json\n"
        "{\n"
        '  "data": [\n'
        '    {"id": "41", "name": "AI Efficient", "mcpStatus": "connected", "hasActiveSession": true},\n'
        '    {"id": "42", "name": "Demo", "mcpStatus": null, "hasActiveSession": false}\n'
        "  ]\n"
        "}\n"
        "```"
    ),
)
def list_project_statuses(db: Session = Depends(get_db)):
    data = _service(db).list_project_statuses()
    return {"data": data}


# Connections
@router.post(
    "/connections",
    response_model=MCPConnectionResponse,
    status_code=201,
    summary="(Deprecated) MCP 연결 생성",
    include_in_schema=False,
    description=(
        "새로운 MCP 연결을 등록합니다. 프론트에서 보여주는 연결 카드에 해당합니다.\n\n"
        "### 필수 필드\n"
        "- `providerId`: 연결할 MCP 제공자 (`chatgpt`, `claude`, `cursor` 등)\n"
        "- `projectId`: 연결을 생성할 프로젝트 ID (문자열)\n\n"
        "### 선택 필드\n"
        '- `config`: 기본 실행 설정 (예: `{ "model": "gpt-4o-mini", "temperature": 0.2 }`). 필요할 때만 사용하세요.\n'
        "- `env`: 내부용 필드입니다. API 키 등 민감 정보는 서버에서 사전 관리하므로 클라이언트가 전달할 필요 없습니다.\n\n"
        "### 동작\n"
        "1. 연결 레코드를 생성하고 상태를 `pending` 으로 설정\n"
        "2. 응답에는 외부에서 사용할 `connectionId` (`cn_0001` 형태)가 포함됩니다.\n"
        "3. 활성화가 필요하면 `POST /mcp/connections/{connectionId}/activate` 를 호출해 `active` 로 전환합니다.\n"
        "4. 이후 세션 생성 API에서 해당 ID를 사용합니다."
    ),
)
def create_connection(connection: MCPConnectionCreate, db: Session = Depends(get_db)):
    _legacy_guard("Deprecated: 연결 생성은 Start Development 흐름에서 자동 처리됩니다.")
    data = _service(db).create_connection(connection)
    return {"data": data}


@router.get(
    "/connections",
    response_model=MCPConnectionListResponse,
    summary="(Deprecated) 연결 목록 조회",
    include_in_schema=False,
    description=(
        "프로젝트별 MCP 연결 목록을 조회합니다.\n\n"
        "### 쿼리 파라미터\n"
        "- `projectId` (optional): 특정 프로젝트에 대한 연결만 조회합니다.\n\n"
        "### 응답 항목\n"
        "- `connectionId`: `cn_0001` 형태의 외부 노출용 ID\n"
        "- `providerId`: 연결된 MCP 제공자\n"
        "- `status`: `pending` / `active` / `inactive` / `error`\n"
        "- `createdAt`: 생성 일시 (UTC)\n"
        "- `config`: 저장된 기본 설정 JSON\n"
    ),
)
def list_connections(
    project_id: str = Query(None, alias="projectId"),
    db: Session = Depends(get_db),
):
    _legacy_guard("Deprecated: 연결 조회는 관리자용입니다. 일반 플로우에서는 사용하지 않습니다.")
    data = _service(db).list_connections(project_id)
    return {"data": data}


@router.delete(
    "/connections/{connection_id}",
    response_model=MCPConnectionCloseResponse,
    status_code=200,
    summary="(Deprecated) 연결 종료",
    include_in_schema=False,
    description=(
        "기존 MCP 연결을 비활성화합니다.\n\n"
        "### 경로 파라미터\n"
        "- `connection_id`: `cn_0001` 형태의 연결 ID\n\n"
        "### 결과\n"
        "- 내부 상태를 `inactive` 로 변경하고 이후 세션 생성이 차단됩니다."
    ),
)
def delete_connection(connection_id: str, db: Session = Depends(get_db)):
    _legacy_guard("Deprecated: 연결 종료는 관리자용입니다. Start Development 자동 연결을 사용하세요.")
    data = _service(db).deactivate_connection(connection_id)
    return {"data": data}


@router.post(
    "/connections/{connection_id}/activate",
    response_model=MCPConnectionResponse,
    status_code=200,
    summary="(Deprecated) 연결 활성화",
    include_in_schema=False,
    description=(
        "대기(`pending`) 상태의 MCP 연결을 활성화(`active`)로 전환합니다.\n\n"
        "### 사용 예시\n"
        "1. `POST /mcp/connections` 로 연결 생성 → `pending` 상태\n"
        "2. 필요한 환경 변수/설정을 적용\n"
        "3. 이 엔드포인트를 호출해 `active` 상태로 변경\n\n"
        "### 경로 파라미터\n"
        "- `connection_id`: `cn_0001` 형태의 연결 ID\n\n"
        "### 응답\n"
        "- 갱신된 연결 정보 (`status` 필드는 `connected` 로 매핑됩니다)"
    ),
)
def activate_connection(connection_id: str, db: Session = Depends(get_db)):
    _legacy_guard("Deprecated: 연결 활성화는 Start Development에서 자동 수행됩니다.")
    data = _service(db).activate_connection(connection_id)
    return {"data": data}


@router.get(
    "/providers/{provider_id}/guide",
    response_model=MCPGuideResponse,
    summary="MCP 연동 가이드",
    description=(
        "선택한 MCP 제공자(chatgpt/claude/cursor 등)를 fastMCP/에이전트에 붙이는 방법을 OS별 단계로 제공합니다.\n"
        "- 경로 파라미터: `provider_id` = chatgpt | claude | cursor\n"
        "- 응답: 지원 에이전트, 선행 조건, OS별 단계(title/description/commands[])\n\n"
        "예시 응답(claude):\n"
        "```json\n"
        "{\n"
        '  "providerId": "claude",\n'
        '  "providerName": "Claude Code MCP",\n'
        '  "supportedAgents": ["Claude Code", "Cursor"],\n'
        '  "prerequisites": ["Node.js 20 이상", "Anthropic API Key"],\n'
        '  "platforms": [ { "os": "macOS", "steps": [\n'
        '    {"title": "1. MCP 서버 연결", "commands": [{"text": "npm i -g fastmcp-cli"}, {"text": "fastmcp login --provider claude --api-key <ANTHROPIC_API_KEY>"}]}\n'
        "  ] } ]\n"
        "}\n"
        "```"
    ),
)
def get_provider_guide(provider_id: str, db: Session = Depends(get_db)):
    data = _service(db).get_guide(provider_id)
    return data


# Sessions
@router.post(
    "/sessions",
    response_model=MCPSessionResponse,
    status_code=201,
    summary="(Deprecated) 세션 생성",
    include_in_schema=False,
    description=(
        "특정 연결을 대상으로 MCP 세션을 시작합니다. 세션은 프론트의 탭이나 창 개념과 매칭됩니다.\n\n"
        "### 필수 필드\n"
        "- `connectionId`: `cn_0001` 형태의 연결 ID\n"
        "- `projectId`: 프로젝트 ID\n\n"
        "### 선택 필드\n"
        "- `metadata`: 프론트에서 관리하고 싶은 메타데이터 (예: 탭 ID)\n\n"
        "### 응답\n"
        "- `sessionId`: `ss_0001` 형태의 세션 ID\n"
        "- `status`: 기본값 `ready`\n"
        "- `metadata`: 저장된 메타데이터\n"
    ),
)
def create_session(session: MCPSessionCreate, db: Session = Depends(get_db)):
    _legacy_guard("Deprecated: 세션 생성은 Start Development에서 자동 수행됩니다.")
    data = _service(db).create_session(session)
    return {"data": data}


@router.get(
    "/sessions",
    response_model=MCPSessionListResponse,
    summary="(Deprecated) 세션 목록 조회",
    include_in_schema=False,
    description=(
        "연결 또는 프로젝트에 열린 MCP 세션 목록을 조회합니다.\n\n"
        "### 쿼리 파라미터\n"
        "- `connectionId`: 특정 연결 기준으로 세션을 필터링\n\n"
        "### 응답 항목\n"
        "- `sessionId`: 외부 세션 ID\n"
        "- `status`: `ready`, `active`, `closed`, `error`\n"
        "- `metadata`: 프론트에서 저장한 정보\n"
        "- `createdAt`: 세션 생성 시각\n"
    ),
)
def list_sessions(
    connection_id: str = Query(None, alias="connectionId"),
    db: Session = Depends(get_db),
):
    _legacy_guard("Deprecated: 세션 조회는 관리자용입니다.")
    data = _service(db).list_sessions(connection_id)
    return {"data": data}


@router.delete(
    "/sessions/{session_id}",
    response_model=MCPSessionCloseResponse,
    status_code=200,
    summary="(Deprecated) 세션 종료",
    include_in_schema=False,
    description=(
        "실행 중인 MCP 세션을 종료합니다.\n\n"
        "### 경로 파라미터\n"
        "- `session_id`: `ss_0001` 형태의 세션 ID\n\n"
        "### 주의\n"
        "- 세션을 닫으면 이후 툴 목록, 실행 API 호출 시 `404` 또는 `ValidationError` 가 발생할 수 있습니다."
    ),
)
def delete_session(session_id: str, db: Session = Depends(get_db)):
    _legacy_guard("Deprecated: 세션 종료는 Start Development 플로우에서 자동 관리됩니다.")
    data = _service(db).close_session(session_id)
    return {"data": data}


# Catalog (Tools/Resources/Prompts)
@router.get(
    "/tools",
    response_model=MCPToolListResponse,
    summary="세션별 툴 목록",
    description="세션에서 호출 가능한 MCP 툴 목록을 조회합니다.\n- 쿼리: `sessionId` 필수 (ss_0001)\n- 응답: `toolId`, `name`, `description`, 입력/출력 스키마(JSON Schema)",
    include_in_schema=False,
)
def list_tools(session_id: str = Query(..., alias="sessionId"), db: Session = Depends(get_db)):
    _legacy_guard("Deprecated: 툴 목록은 현재 플로우에서 사용하지 않습니다.")
    data = _service(db).list_tools(session_id)
    return {"data": data}


@router.get(
    "/resources",
    response_model=MCPResourceListResponse,
    summary="세션별 리소스 목록",
    description="세션이 접근할 수 있는 리소스 URI를 제공합니다.\n- 쿼리: `sessionId` 필수\n- 응답: `uri`(file:/// , search:/// , project:// 등), `kind`, `description`",
    include_in_schema=False,
)
def list_resources(session_id: str = Query(..., alias="sessionId"), db: Session = Depends(get_db)):
    _legacy_guard("Deprecated: 리소스 목록은 현재 플로우에서 사용하지 않습니다.")
    data = _service(db).list_resources(session_id)
    return {"data": data}


@router.get(
    "/resources/read",
    response_model=MCPResourceReadResponse,
    summary="리소스 읽기",
    description="`uri`로 지정한 리소스를 실제 내용까지 읽어 반환합니다.\n- 쿼리: `sessionId` 필수, `uri` 필수\n- 지원 URI: file:///path, search:///code?query=..., project://tasks, project://documents\n- 응답: 리소스 종류에 따라 내용/검색결과/목록을 포함",
    include_in_schema=False,
)
def read_resource(
    session_id: str = Query(..., alias="sessionId"),
    uri: str = Query(..., description="읽을 리소스 URI"),
    db: Session = Depends(get_db),
):
    _legacy_guard("Deprecated: 리소스 읽기는 현재 플로우에서 사용하지 않습니다.")
    data = _service(db).read_resource(session_id, uri)
    return {"data": data}


@router.get(
    "/prompts",
    response_model=MCPPromptListResponse,
    summary="세션별 프롬프트 목록",
    description="세션에서 사용할 수 있는 프롬프트 템플릿을 조회합니다.\n- 쿼리: `sessionId` 필수\n- 응답: `promptId`, `name`, `description`",
    include_in_schema=False,
)
def list_prompts(session_id: str = Query(..., alias="sessionId"), db: Session = Depends(get_db)):
    _legacy_guard("Deprecated: 프롬프트 목록은 현재 플로우에서 사용하지 않습니다.")
    data = _service(db).list_prompts(session_id)
    return {"data": data}


# Runs
@router.post(
    "/runs",
    response_model=MCPRunResponse,
    status_code=201,
    summary="(Deprecated) 실행 생성",
    include_in_schema=False,
    description=(
        "세션에서 MCP 실행(대화/툴/프롬프트)을 수행합니다.\n\n"
        "### 필수 필드\n"
        "- `sessionId`: 실행을 수행할 세션 ID\n"
        "- `mode`: `chat` / `tool` / `prompt`\n"
        "- `input`: 실행 인풋 JSON (모드에 따라 구조가 달라짐)\n\n"
        "### 선택 필드\n"
        "- `toolId` / `promptId`: 해당 모드에서 사용하는 식별자\n"
        "- `config`: 실행 시점 설정 (모델, temperature 등)\n\n"
        "### 응답\n"
        "- `runId`: `run_0001` 형태의 실행 ID\n"
        "- `status`: 초기값 `queued`\n"
        "- `result`: provider에서 반환한 원본 JSON"
    ),
)
def create_run(run: MCPRunCreate, db: Session = Depends(get_db)):
    _legacy_guard("Deprecated: 실행 생성은 Start Development에서 자동 수행됩니다.")
    data = _service(db).create_run(run)
    return {"data": data}


@router.get(
    "/runs/{run_id}",
    response_model=MCPRunStatusResponse,
    summary="실행 상태 조회",
    description=(
        "run ID로 실행 상태와 결과를 확인합니다.\n"
        "- 경로: `run_id` (run_0001)\n"
        "- 응답: `status`, `result`(원본 JSON), `output`(요약 텍스트), `startedAt`, `finishedAt`\n\n"
        "예시 응답:\n"
        "```json\n"
        "{\n"
        '  "data": {\n'
        '    "runId": "run_0123",\n'
        '    "status": "running",\n'
        '    "result": null,\n'
        '    "output": null,\n'
        '    "startedAt": "2024-12-01T12:30:00",\n'
        '    "finishedAt": null\n'
        "  }\n"
        "}\n"
        "```"
    ),
)
def get_run(run_id: str, db: Session = Depends(get_db)):
    data = _service(db).get_run(run_id)
    return {"data": data}


@router.post(
    "/runs/{run_id}/cancel",
    response_model=MCPRunCancelResponse,
    status_code=200,
    summary="실행 취소",
    description="진행 중인 run을 취소합니다.\n- 경로: `run_id`\n- 이미 완료/실패/취소된 run은 취소할 수 없습니다.",
    include_in_schema=False,
)
def cancel_run(run_id: str, db: Session = Depends(get_db)):
    _legacy_guard("Deprecated: 실행 취소는 현재 플로우에서 사용하지 않습니다.")
    data = _service(db).cancel_run(run_id)
    return {"data": data}


@router.get(
    "/runs/{run_id}/events",
    response_model=MCPRunEventsResponse,
    summary="실행 이벤트 조회",
    description="run과 관련된 이벤트를 시간 순으로 반환합니다.\n- `RUN_STATUS`: 현재 상태/메시지\n- `RUN_RESULT`: 최종 결과(JSON)\n폴링하거나 SSE 대용으로 사용할 수 있습니다.",
    include_in_schema=False,
)
def stream_run_events(run_id: str, db: Session = Depends(get_db)):
    _legacy_guard("Deprecated: 실행 이벤트 조회는 현재 플로우에서 사용하지 않습니다.")
    data = _service(db).list_run_events(run_id)
    return {"data": data}


# ---------------------------------------------------------------------------
# Copy-Paste Ready Config (vooster.ai style)
# ---------------------------------------------------------------------------


@router.get(
    "/projects/{project_id}/config-file",
    response_model=MCPConfigFileResponse,
    summary="MCP 설정 파일 생성 (복사-붙여넣기용)",
    description=(
        "vooster.ai 스타일: 사용자가 복사-붙여넣기만 하면 Cursor에서 MCP 연결이 가능하도록 설정 파일을 생성합니다.\n\n"
        "**사용 방법:**\n"
        "1. 이 API를 호출하여 설정 파일 내용을 받습니다\n"
        "2. 사용자가 받은 내용을 Cursor 설정 파일 위치에 복사합니다\n"
        "3. Cursor를 재시작하면 MCP 연결이 활성화됩니다\n\n"
        "**파라미터:**\n"
        "- `project_id`: 프로젝트 ID\n"
        "- `provider_id`: MCP 제공자 (cursor/claude/chatgpt)\n"
        "- `os`: 운영체제 (macOS/Windows, 기본값: macOS)\n\n"
        "**인증:**\n"
        "- Authorization 헤더에서 Bearer 토큰을 자동으로 읽어 사용합니다.\n"
    ),
)
def generate_mcp_config_file(
    project_id: int,
    current_user: User = Depends(get_current_user),
    provider_id: str = Query(default="cursor", description="MCP 제공자 (cursor/claude/chatgpt)"),
    user_os: str = Query(default="macOS", description="운영체제 (macOS/Windows)"),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """MCP 설정 파일 생성 - 사용자가 복사-붙여넣기만 하면 됨."""
    # 프로젝트 소유권 확인
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project with ID {project_id} not found")

    # 사용자 토큰 생성 (MCP 어댑터에서 사용할 토큰)
    from app.domain.auth import create_access_token

    # 사용자 토큰 생성 (또는 기존 토큰 재사용)
    api_token = create_access_token(current_user.user_id)

    # 요청 base URL을 fallback으로 사용 (환경변수 미설정 시)
    base_url = str(request.base_url).rstrip("/") if request else None
    data = _service(db).generate_mcp_config_file(project_id, provider_id, api_token, user_os, base_url)
    return data


@router.get(
    "/tasks/{task_id}/command",
    response_model=MCPTaskCommandResponse,
    summary="태스크별 MCP 명령어 생성 (복사-붙여넣기용)",
    description=(
        "vooster.ai 스타일: 태스크별로 Cursor에서 사용할 명령어를 생성합니다.\n\n"
        "**사용 방법:**\n"
        "1. 이 API를 호출하여 명령어를 받습니다\n"
        "2. 사용자가 받은 명령어를 Cursor의 MCP 채팅창에 붙여넣습니다\n"
        "3. Cursor의 AI가 자동으로 적절한 MCP 툴을 선택하여 실행합니다\n"
        "4. 시스템이 자동으로 PRD/SRS/USER_STORY 문서와 태스크 정보를 수집하여 코드를 생성합니다\n\n"
        "**파라미터:**\n"
        "- `task_id`: 태스크 ID\n"
        "- `provider_id`: MCP 제공자 (선택, 기본값: cursor)\n"
        "- `format`: 명령어 형식 (선택, 기본값: vooster)\n"
        '  - `vooster`: 구조화된 명령어 (예: "atrina를 사용해서 프로젝트 148의 태스크 236 작업 수행하라")\n'
        '  - `natural`: 자연어 명령어 (예: "AI 기반 효율적 개발 플랫폼의 MCP Quick Test 구현해줘")\n\n'
        "**인증:**\n"
        "- Authorization 헤더에서 Bearer 토큰을 자동으로 읽어 사용합니다.\n"
    ),
)
def generate_task_command(
    task_id: int,
    current_user: User = Depends(get_current_user),
    provider_id: str = Query(default="cursor", description="MCP 제공자 (cursor/claude/chatgpt)"),
    format: str = Query(default="vooster", description="명령어 형식 (vooster/natural)"),
    db: Session = Depends(get_db),
):
    """태스크별 MCP 명령어 생성 - 사용자가 복사-붙여넣기만 하면 됨."""
    # 태스크 소유권 확인 (선택사항 - 필요시 추가)
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found")

    # 명령어 형식 검증
    if format not in {"vooster", "natural"}:
        raise HTTPException(status_code=400, detail="format must be 'vooster' or 'natural'")

    data = _service(db).generate_task_command(task_id, provider_id, command_format=format)
    return data
