"""MCP (Model Context Protocol) API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.domain.mcp import MCPService
from app.schemas.mcp import (
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
    MCPToolListResponse,
)

router = APIRouter(prefix="/mcp", tags=["mcp"])


def _service(db: Session) -> MCPService:
    return MCPService(db)


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
        "- `mcpStatus`: `connected`(활성 연결 있음) / `pending`(생성만 함) / `None`(연결 없음)\n"
        "- `hasActiveSession`: 현재 열린 세션이 있는지 여부"
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
    raise HTTPException(
        status_code=410,
        detail="Deprecated: 연결 생성은 Start Development 흐름에서 자동 처리됩니다.",
    )


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
    raise HTTPException(
        status_code=410,
        detail="Deprecated: 연결 조회는 관리자용입니다. 일반 플로우에서는 사용하지 않습니다.",
    )


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
    raise HTTPException(
        status_code=410,
        detail="Deprecated: 연결 종료는 관리자용입니다. Start Development 자동 연결을 사용하세요.",
    )


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
    raise HTTPException(
        status_code=410,
        detail="Deprecated: 연결 활성화는 Start Development에서 자동 수행됩니다.",
    )


@router.get(
    "/providers/{provider_id}/guide",
    response_model=MCPGuideResponse,
    summary="MCP 연동 가이드",
    description=(
        "선택한 MCP 제공자(chatgpt/claude/cursor 등)를 fastMCP/에이전트에 붙이는 방법을 OS별 단계로 제공합니다.\n"
        "- 경로 파라미터: `provider_id` = chatgpt | claude | cursor\n"
        "- 응답: 지원 에이전트, 선행 조건, OS별 단계(title/description/commands[])"
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
    raise HTTPException(
        status_code=410,
        detail="Deprecated: 세션 생성은 Start Development에서 자동 수행됩니다.",
    )


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
    raise HTTPException(
        status_code=410,
        detail="Deprecated: 세션 조회는 관리자용입니다.",
    )


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
    raise HTTPException(
        status_code=410,
        detail="Deprecated: 세션 종료는 Start Development 플로우에서 자동 관리됩니다.",
    )


# Catalog (Tools/Resources/Prompts)
@router.get(
    "/tools",
    response_model=MCPToolListResponse,
    summary="세션별 툴 목록",
    description=(
        "세션에서 호출 가능한 MCP 툴 목록을 조회합니다.\n"
        "- 쿼리: `sessionId` 필수 (ss_0001)\n"
        "- 응답: `toolId`, `name`, `description`, 입력/출력 스키마(JSON Schema)"
    ),
)
def list_tools(session_id: str = Query(..., alias="sessionId"), db: Session = Depends(get_db)):
    data = _service(db).list_tools(external_session_id=session_id)
    return {"data": data}


@router.get(
    "/resources",
    response_model=MCPResourceListResponse,
    summary="세션별 리소스 목록",
    description=(
        "세션이 접근할 수 있는 리소스 URI를 제공합니다.\n"
        "- 쿼리: `sessionId` 필수\n"
        "- 응답: `uri`(file:/// , search:/// , project:// 등), `kind`, `description`"
    ),
)
def list_resources(session_id: str = Query(..., alias="sessionId"), db: Session = Depends(get_db)):
    data = _service(db).list_resources(external_session_id=session_id)
    return {"data": data}


@router.get(
    "/resources/read",
    response_model=MCPResourceReadResponse,
    summary="리소스 읽기",
    description=(
        "`uri`로 지정한 리소스를 실제 내용까지 읽어 반환합니다.\n"
        "- 쿼리: `sessionId` 필수, `uri` 필수\n"
        "- 지원 URI: file:///path, search:///code?query=..., project://tasks, project://documents\n"
        "- 응답: 리소스 종류에 따라 내용/검색결과/목록을 포함"
    ),
)
def read_resource(
    session_id: str = Query(..., alias="sessionId"),
    uri: str = Query(..., description="읽을 리소스 URI"),
    db: Session = Depends(get_db),
):
    data = _service(db).read_resource(external_session_id=session_id, uri=uri)
    return {"data": data}


@router.get(
    "/prompts",
    response_model=MCPPromptListResponse,
    summary="세션별 프롬프트 목록",
    description=(
        "세션에서 사용할 수 있는 프롬프트 템플릿을 조회합니다.\n"
        "- 쿼리: `sessionId` 필수\n"
        "- 응답: `promptId`, `name`, `description`"
    ),
)
def list_prompts(session_id: str = Query(..., alias="sessionId"), db: Session = Depends(get_db)):
    data = _service(db).list_prompts(external_session_id=session_id)
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
    raise HTTPException(
        status_code=410,
        detail="Deprecated: 실행 생성은 Start Development에서 자동 수행됩니다.",
    )


@router.get(
    "/runs/{run_id}",
    response_model=MCPRunStatusResponse,
    summary="실행 상태 조회",
    description=(
        "run ID로 실행 상태와 결과를 확인합니다.\n"
        "- 경로: `run_id` (run_0001)\n"
        "- 응답: `status`, `result`(원본 JSON), `output`(요약 텍스트), `startedAt`, `finishedAt`"
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
    description=(
        "진행 중인 run을 취소합니다.\n"
        "- 경로: `run_id`\n"
        "- 이미 완료/실패/취소된 run은 취소할 수 없습니다."
    ),
)
def cancel_run(run_id: str, db: Session = Depends(get_db)):
    data = _service(db).cancel_run(run_id)
    return {"data": data}


@router.get(
    "/runs/{run_id}/events",
    response_model=MCPRunEventsResponse,
    summary="실행 이벤트 조회",
    description=(
        "run과 관련된 이벤트를 시간 순으로 반환합니다.\n"
        "- `RUN_STATUS`: 현재 상태/메시지\n"
        "- `RUN_RESULT`: 최종 결과(JSON)\n"
        "폴링하거나 SSE 대용으로 사용할 수 있습니다."
    ),
)
def stream_run_events(run_id: str, db: Session = Depends(get_db)):
    data = _service(db).list_run_events(run_id)
    return {"data": data}
