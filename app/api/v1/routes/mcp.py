"""MCP (Model Context Protocol) API routes."""

from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.domain.mcp import MCPService
from app.schemas.mcp import (
    MCPConnectionCreate,
    MCPConnectionResponse,
    MCPConnectionListResponse,
    MCPConnectionCloseResponse,
    MCPProjectStatusResponse,
    MCPSessionCreate,
    MCPSessionResponse,
    MCPSessionListResponse,
    MCPSessionCloseResponse,
    MCPRunCreate,
    MCPRunResponse,
    MCPRunStatusResponse,
    MCPRunCancelResponse,
    MCPRunEventsResponse,
    MCPToolListResponse,
    MCPResourceListResponse,
    MCPPromptListResponse,
    MCPGuideResponse,
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
        "모든 프로젝트의 MCP 연결 상태를 한눈에 확인합니다.\n\n"
        "### 응답 데이터\n"
        "- `id`: 프로젝트 ID (문자열)\n"
        "- `name`: 프로젝트 이름\n"
        "- `mcpStatus`: `connected` / `pending` / `None`\n"
        "    - `connected`: 활성 연결이 하나 이상 존재\n"
        "    - `pending`: 연결 생성은 되었지만 활성화 전\n"
        "    - `None`: MCP 연결이 아직 없음\n"
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
    summary="MCP 연결 생성",
    description=(
        "새로운 MCP 연결을 등록합니다. 프론트에서 보여주는 연결 카드에 해당합니다.\n\n"
        "### 필수 필드\n"
        "- `providerId`: 연결할 MCP 제공자 (`chatgpt`, `claude`, `cursor` 등)\n"
        "- `projectId`: 연결을 생성할 프로젝트 ID (문자열)\n\n"
        "### 선택 필드\n"
        "- `config`: 기본 실행 설정 (예: `{ \"model\": \"gpt-4o-mini\", \"temperature\": 0.2 }`). 필요할 때만 사용하세요.\n"
        "- `env`: 내부용 필드입니다. API 키 등 민감 정보는 서버에서 사전 관리하므로 클라이언트가 전달할 필요 없습니다.\n\n"
        "### 동작\n"
        "1. 연결 레코드를 생성하고 상태를 `pending` 으로 설정\n"
        "2. 응답에는 외부에서 사용할 `connectionId` (`cn_0001` 형태)가 포함됩니다.\n"
        "3. 활성화가 필요하면 `POST /mcp/connections/{connectionId}/activate` 를 호출해 `active` 로 전환합니다.\n"
        "4. 이후 세션 생성 API에서 해당 ID를 사용합니다."
    ),
)
def create_connection(connection: MCPConnectionCreate, db: Session = Depends(get_db)):
    data = _service(db).create_connection(connection)
    return {"data": data}


@router.get(
    "/connections",
    response_model=MCPConnectionListResponse,
    summary="연결 목록 조회",
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
    data = _service(db).list_connections(project_identifier=project_id)
    return {"data": data}


@router.delete(
    "/connections/{connection_id}",
    response_model=MCPConnectionCloseResponse,
    status_code=200,
    summary="연결 종료",
    description=(
        "기존 MCP 연결을 비활성화합니다.\n\n"
        "### 경로 파라미터\n"
        "- `connection_id`: `cn_0001` 형태의 연결 ID\n\n"
        "### 결과\n"
        "- 내부 상태를 `inactive` 로 변경하고 이후 세션 생성이 차단됩니다."
    ),
)
def delete_connection(connection_id: str, db: Session = Depends(get_db)):
    data = _service(db).deactivate_connection(connection_id)
    return {"data": data}


@router.post(
    "/connections/{connection_id}/activate",
    response_model=MCPConnectionResponse,
    status_code=200,
    summary="연결 활성화",
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
    data = _service(db).activate_connection(connection_id)
    return {"data": data}


@router.get(
    "/providers/{provider_id}/guide",
    response_model=MCPGuideResponse,
    summary="MCP 연동 가이드 조회",
    description=(
        "선택한 MCP 제공자를 fastMCP/에이전트에 연결하는 방법을 안내합니다.\n\n"
        "### 경로 파라미터\n"
        "- `provider_id`: `chatgpt`, `claude`, `cursor` 등 제공자 ID\n\n"
        "### 응답 구조\n"
        "- `supportedAgents`: 지원되는 에이전트 목록 (예: Cursor, Claude Code)\n"
        "- `prerequisites`: 사전 준비 사항 (Node.js 버전, API Key 등)\n"
        "- `platforms`: 운영체제별 단계별 명령어와 설명\n\n"
        "프런트에서는 이 데이터를 기반으로 모달/가이드를 렌더링할 수 있습니다."
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
    summary="세션 생성",
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
    data = _service(db).create_session(session)
    return {"data": data}


@router.get(
    "/sessions",
    response_model=MCPSessionListResponse,
    summary="세션 목록 조회",
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
    data = _service(db).list_sessions(connection_identifier=connection_id)
    return {"data": data}


@router.delete(
    "/sessions/{session_id}",
    response_model=MCPSessionCloseResponse,
    status_code=200,
    summary="세션 종료",
    description=(
        "실행 중인 MCP 세션을 종료합니다.\n\n"
        "### 경로 파라미터\n"
        "- `session_id`: `ss_0001` 형태의 세션 ID\n\n"
        "### 주의\n"
        "- 세션을 닫으면 이후 툴 목록, 실행 API 호출 시 `404` 또는 `ValidationError` 가 발생할 수 있습니다."
    ),
)
def delete_session(session_id: str, db: Session = Depends(get_db)):
    data = _service(db).close_session(session_id)
    return {"data": data}


# Catalog (Tools/Resources/Prompts)
@router.get(
    "/tools",
    response_model=MCPToolListResponse,
    summary="세션별 툴 목록",
    description=(
        "선택한 세션에서 호출 가능한 MCP 툴 목록을 가져옵니다.\n\n"
        "### 쿼리 파라미터\n"
        "- `sessionId` (필수): `ss_0001` 형태의 세션 ID\n\n"
        "### 응답 항목\n"
        "- `toolId`: 툴 식별자 (예: `gen_user_story`)\n"
        "- `name`: 프론트에 노출할 이름\n"
        "- `description`: 사용 설명\n"
        "- `inputSchema` / `outputSchema`: JSON Schema 형태의 구조"
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
        "MCP 제공자가 접근 가능한 리소스를 조회합니다. 예) 파일, 검색, 지식베이스 등.\n\n"
        "### 쿼리 파라미터\n"
        "- `sessionId` (필수)\n\n"
        "### 응답 항목\n"
        "- `uri`: `file:///`, `search:///` 등 스킴 포함 식별자\n"
        "- `kind`: 리소스 유형\n"
        "- `description`: 요약 설명"
    ),
)
def list_resources(session_id: str = Query(..., alias="sessionId"), db: Session = Depends(get_db)):
    data = _service(db).list_resources(external_session_id=session_id)
    return {"data": data}


@router.get(
    "/prompts",
    response_model=MCPPromptListResponse,
    summary="세션별 프롬프트 목록",
    description=(
        "연결된 MCP에서 제공하는 프롬프트 템플릿을 조회합니다.\n\n"
        "### 쿼리 파라미터\n"
        "- `sessionId` (필수)\n\n"
        "### 응답 항목\n"
        "- `promptId`: 프롬프트 식별자\n"
        "- `name`: 표시 이름\n"
        "- `description`: 활용 설명"
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
    summary="실행 생성",
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
    data = _service(db).create_run(run)
    return {"data": data}


@router.get(
    "/runs/{run_id}",
    response_model=MCPRunStatusResponse,
    summary="실행 상태 조회",
    description=(
        "특정 실행의 진행 상황을 확인합니다.\n\n"
        "### 경로 파라미터\n"
        "- `run_id`: `run_0001` 형태의 실행 ID\n\n"
        "### 응답 항목\n"
        "- `status`: `queued`, `running`, `succeeded`, `failed`, `cancelled`\n"
        "- `result`: provider가 반환한 JSON 결과\n"
        "- `output`: 프론트에서 바로 노출 가능한 요약 필드 (`outputText` 등)\n"
        "- `startedAt` / `finishedAt`: 실행 시간 정보"
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
        "실행 중인 MCP 작업을 취소합니다.\n\n"
        "### 주의\n"
        "- 이미 `succeeded`, `failed`, `cancelled` 상태인 실행은 취소할 수 없습니다.\n"
        "- 성공 시 `cancelled=true` 와 함께 원본 실행 ID를 반환합니다."
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
        "실행과 관련된 상태/결과 이벤트를 순서대로 반환합니다.\n\n"
        "### 이벤트 타입\n"
        "- `RUN_STATUS`: 현재 상태와 메시지\n"
        "- `RUN_RESULT`: 최종 결과 (성공 시)\n\n"
        "프론트에서 SSE(Stream)처럼 처리하고 싶다면 주기적으로 조회하거나 "
        "추후 실제 스트리밍 엔드포인트로 교체할 수 있습니다."
    ),
)
def stream_run_events(run_id: str, db: Session = Depends(get_db)):
    data = _service(db).list_run_events(run_id)
    return {"data": data}

