"""MCP (Model Context Protocol) API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.mcp import (
    MCPConnectionCreate,
    MCPConnectionResponse,
    MCPSessionCreate,
    MCPSessionResponse,
    MCPRunCreate,
    MCPRunResponse,
    MCPRunStatusResponse,
)

router = APIRouter(prefix="/mcp", tags=["mcp"])


# Connections
@router.post("/connections", response_model=MCPConnectionResponse, status_code=201)
def create_connection(connection: MCPConnectionCreate, db: Session = Depends(get_db)):
    """MCP 연결 생성"""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/connections")
def list_connections(project_id: int = None, db: Session = Depends(get_db)):
    """MCP 연결 목록 조회"""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.delete("/connections/{connection_id}", status_code=204)
def delete_connection(connection_id: int, db: Session = Depends(get_db)):
    """MCP 연결 종료"""
    raise HTTPException(status_code=501, detail="Not implemented")


# Sessions
@router.post("/sessions", response_model=MCPSessionResponse, status_code=201)
def create_session(session: MCPSessionCreate, db: Session = Depends(get_db)):
    """MCP 세션 시작"""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/sessions")
def list_sessions(connection_id: int = None, db: Session = Depends(get_db)):
    """MCP 세션 목록 조회"""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(session_id: int, db: Session = Depends(get_db)):
    """MCP 세션 종료"""
    raise HTTPException(status_code=501, detail="Not implemented")


# Catalog (Tools/Resources/Prompts)
@router.get("/tools")
def list_tools(session_id: int, db: Session = Depends(get_db)):
    """MCP 툴 목록 조회"""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/resources")
def list_resources(session_id: int, db: Session = Depends(get_db)):
    """MCP 리소스 목록 조회"""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/prompts")
def list_prompts(session_id: int, db: Session = Depends(get_db)):
    """MCP 프롬프트 목록 조회"""
    raise HTTPException(status_code=501, detail="Not implemented")


# Runs
@router.post("/runs", response_model=MCPRunResponse, status_code=201)
def create_run(run: MCPRunCreate, db: Session = Depends(get_db)):
    """MCP 실행 생성"""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/runs/{run_id}", response_model=MCPRunStatusResponse)
def get_run(run_id: int, db: Session = Depends(get_db)):
    """MCP 실행 상태 조회"""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/runs/{run_id}/cancel", status_code=200)
def cancel_run(run_id: int, db: Session = Depends(get_db)):
    """MCP 실행 취소"""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/runs/{run_id}/events")
def stream_run_events(run_id: int, db: Session = Depends(get_db)):
    """MCP 실행 이벤트 스트리밍 (SSE)"""
    raise HTTPException(status_code=501, detail="Not implemented")

