"""MCP (Model Context Protocol) API routes."""

from typing import List

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.domain.mcp import MCPService
from app.schemas.mcp import (
    MCPConnectionCreate,
    MCPConnectionResponse,
    MCPProjectStatusResponse,
    MCPSessionCreate,
    MCPSessionResponse,
    MCPRunCreate,
    MCPRunResponse,
    MCPRunStatusResponse,
)

router = APIRouter(prefix="/mcp", tags=["mcp"])


def _service(db: Session) -> MCPService:
    return MCPService(db)


# Project summary
@router.get("/projects", response_model=List[MCPProjectStatusResponse])
def list_project_statuses(db: Session = Depends(get_db)):
    """프로젝트별 MCP 상태 조회"""
    return _service(db).list_project_statuses()


# Connections
@router.post("/connections", response_model=MCPConnectionResponse, status_code=201)
def create_connection(connection: MCPConnectionCreate, db: Session = Depends(get_db)):
    """MCP 연결 생성"""
    return _service(db).create_connection(connection)


@router.get("/connections", response_model=List[MCPConnectionResponse])
def list_connections(project_id: int = None, db: Session = Depends(get_db)):
    """MCP 연결 목록 조회"""
    return _service(db).list_connections(project_id=project_id)


@router.delete("/connections/{connection_id}", status_code=204)
def delete_connection(connection_id: int, db: Session = Depends(get_db)):
    """MCP 연결 종료"""
    _service(db).deactivate_connection(connection_id)
    return Response(status_code=204)


# Sessions
@router.post("/sessions", response_model=MCPSessionResponse, status_code=201)
def create_session(session: MCPSessionCreate, db: Session = Depends(get_db)):
    """MCP 세션 시작"""
    return _service(db).create_session(session)


@router.get("/sessions", response_model=List[MCPSessionResponse])
def list_sessions(connection_id: int = None, db: Session = Depends(get_db)):
    """MCP 세션 목록 조회"""
    return _service(db).list_sessions(connection_id=connection_id)


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(session_id: int, db: Session = Depends(get_db)):
    """MCP 세션 종료"""
    _service(db).close_session(session_id)
    return Response(status_code=204)


# Catalog (Tools/Resources/Prompts)
@router.get("/tools")
def list_tools(session_id: int, db: Session = Depends(get_db)):
    """MCP 툴 목록 조회"""
    return _service(db).list_tools(session_id=session_id)


@router.get("/resources")
def list_resources(session_id: int, db: Session = Depends(get_db)):
    """MCP 리소스 목록 조회"""
    return _service(db).list_resources(session_id=session_id)


@router.get("/prompts")
def list_prompts(session_id: int, db: Session = Depends(get_db)):
    """MCP 프롬프트 목록 조회"""
    return _service(db).list_prompts(session_id=session_id)


# Runs
@router.post("/runs", response_model=MCPRunResponse, status_code=201)
def create_run(run: MCPRunCreate, db: Session = Depends(get_db)):
    """MCP 실행 생성"""
    return _service(db).create_run(run)


@router.get("/runs/{run_id}", response_model=MCPRunStatusResponse)
def get_run(run_id: int, db: Session = Depends(get_db)):
    """MCP 실행 상태 조회"""
    return _service(db).get_run(run_id)


@router.post("/runs/{run_id}/cancel", status_code=200)
def cancel_run(run_id: int, db: Session = Depends(get_db)):
    """MCP 실행 취소"""
    return _service(db).cancel_run(run_id)


@router.get("/runs/{run_id}/events")
def stream_run_events(run_id: int, db: Session = Depends(get_db)):
    """MCP 실행 이벤트 스트리밍 (SSE)"""
    return _service(db).list_run_events(run_id)

