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
)

router = APIRouter(prefix="/mcp", tags=["mcp"])


def _service(db: Session) -> MCPService:
    return MCPService(db)


# Project summary
@router.get("/projects", response_model=MCPProjectStatusResponse)
def list_project_statuses(db: Session = Depends(get_db)):
    """프로젝트별 MCP 상태 조회"""
    data = _service(db).list_project_statuses()
    return {"data": data}


# Connections
@router.post("/connections", response_model=MCPConnectionResponse, status_code=201)
def create_connection(connection: MCPConnectionCreate, db: Session = Depends(get_db)):
    """MCP 연결 생성"""
    data = _service(db).create_connection(connection)
    return {"data": data}


@router.get("/connections", response_model=MCPConnectionListResponse)
def list_connections(
    project_id: str = Query(None, alias="projectId"),
    db: Session = Depends(get_db),
):
    """MCP 연결 목록 조회"""
    data = _service(db).list_connections(project_identifier=project_id)
    return {"data": data}


@router.delete(
    "/connections/{connection_id}",
    response_model=MCPConnectionCloseResponse,
    status_code=200,
)
def delete_connection(connection_id: str, db: Session = Depends(get_db)):
    """MCP 연결 종료"""
    data = _service(db).deactivate_connection(connection_id)
    return {"data": data}


# Sessions
@router.post("/sessions", response_model=MCPSessionResponse, status_code=201)
def create_session(session: MCPSessionCreate, db: Session = Depends(get_db)):
    """MCP 세션 시작"""
    data = _service(db).create_session(session)
    return {"data": data}


@router.get("/sessions", response_model=MCPSessionListResponse)
def list_sessions(
    connection_id: str = Query(None, alias="connectionId"),
    db: Session = Depends(get_db),
):
    """MCP 세션 목록 조회"""
    data = _service(db).list_sessions(connection_identifier=connection_id)
    return {"data": data}


@router.delete(
    "/sessions/{session_id}",
    response_model=MCPSessionCloseResponse,
    status_code=200,
)
def delete_session(session_id: str, db: Session = Depends(get_db)):
    """MCP 세션 종료"""
    data = _service(db).close_session(session_id)
    return {"data": data}


# Catalog (Tools/Resources/Prompts)
@router.get("/tools", response_model=MCPToolListResponse)
def list_tools(session_id: str = Query(..., alias="sessionId"), db: Session = Depends(get_db)):
    """MCP 툴 목록 조회"""
    data = _service(db).list_tools(external_session_id=session_id)
    return {"data": data}


@router.get("/resources", response_model=MCPResourceListResponse)
def list_resources(session_id: str = Query(..., alias="sessionId"), db: Session = Depends(get_db)):
    """MCP 리소스 목록 조회"""
    data = _service(db).list_resources(external_session_id=session_id)
    return {"data": data}


@router.get("/prompts", response_model=MCPPromptListResponse)
def list_prompts(session_id: str = Query(..., alias="sessionId"), db: Session = Depends(get_db)):
    """MCP 프롬프트 목록 조회"""
    data = _service(db).list_prompts(external_session_id=session_id)
    return {"data": data}


# Runs
@router.post("/runs", response_model=MCPRunResponse, status_code=201)
def create_run(run: MCPRunCreate, db: Session = Depends(get_db)):
    """MCP 실행 생성"""
    data = _service(db).create_run(run)
    return {"data": data}


@router.get("/runs/{run_id}", response_model=MCPRunStatusResponse)
def get_run(run_id: str, db: Session = Depends(get_db)):
    """MCP 실행 상태 조회"""
    data = _service(db).get_run(run_id)
    return {"data": data}


@router.post("/runs/{run_id}/cancel", response_model=MCPRunCancelResponse, status_code=200)
def cancel_run(run_id: str, db: Session = Depends(get_db)):
    """MCP 실행 취소"""
    data = _service(db).cancel_run(run_id)
    return {"data": data}


@router.get("/runs/{run_id}/events", response_model=MCPRunEventsResponse)
def stream_run_events(run_id: str, db: Session = Depends(get_db)):
    """MCP 실행 이벤트 스트리밍 (SSE)"""
    data = _service(db).list_run_events(run_id)
    return {"data": data}

