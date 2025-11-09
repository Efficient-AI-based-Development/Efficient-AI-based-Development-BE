"""MCP (Model Context Protocol) related Pydantic schemas."""

from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict


# Connection 관련
class MCPConnectionCreate(BaseModel):
    """MCP 연결 생성 요청 스키마
    
    POST /api/mcp/connections 요청 시 사용
    """
    project_id: int = Field(..., description="프로젝트 ID")
    connection_type: str = Field(
        default="cursor",
        description="연결 타입",
        examples=["cursor"]
    )


class MCPConnectionResponse(BaseModel):
    """MCP 연결 응답 스키마"""
    id: int
    project_id: int
    connection_type: str
    status: str = Field(..., description="연결 상태")
    created_at: datetime
    updated_at: datetime
    setup_commands: List[str] = Field(default_factory=list, description="연동을 위한 CLI 명령어 목록")
    
    model_config = ConfigDict(from_attributes=True)


# Session 관련
class MCPSessionCreate(BaseModel):
    """MCP 세션 시작 요청 스키마
    
    POST /api/mcp/sessions 요청 시 사용
    """
    connection_id: int = Field(..., description="연결 ID")
    context: Optional[dict] = Field(None, description="세션 컨텍스트")


class MCPSessionResponse(BaseModel):
    """MCP 세션 응답 스키마"""
    id: int
    connection_id: int
    status: str
    context: Optional[dict] = Field(None, description="세션 컨텍스트")
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Tool 관련
class MCPToolResponse(BaseModel):
    """MCP 툴 응답 스키마
    
    GET /api/mcp/tools?sessionId=... 응답 시 사용
    """
    name: str
    description: str
    parameters: Optional[dict] = Field(None, description="툴 파라미터")


class MCPToolListResponse(BaseModel):
    """MCP 툴 목록 응답 스키마"""
    items: List[MCPToolResponse]
    total: int


# Resource 관련
class MCPResourceResponse(BaseModel):
    """MCP 리소스 응답 스키마
    
    GET /api/mcp/resources?sessionId=... 응답 시 사용
    """
    uri: str
    name: str
    description: Optional[str]


class MCPResourceListResponse(BaseModel):
    """MCP 리소스 목록 응답 스키마"""
    items: List[MCPResourceResponse]
    total: int


# Prompt 관련
class MCPPromptResponse(BaseModel):
    """MCP 프롬프트 응답 스키마
    
    GET /api/mcp/prompts?sessionId=... 응답 시 사용
    """
    name: str
    description: str
    arguments: Optional[list] = Field(None, description="프롬프트 인자")


class MCPPromptListResponse(BaseModel):
    """MCP 프롬프트 목록 응답 스키마"""
    items: List[MCPPromptResponse]
    total: int


# Run 관련
class MCPRunCreate(BaseModel):
    """MCP 실행 생성 요청 스키마
    
    POST /api/mcp/runs 요청 시 사용
    """
    session_id: int = Field(..., description="세션 ID")
    tool_name: Optional[str] = Field(None, description="툴 이름")
    prompt_name: Optional[str] = Field(None, description="프롬프트 이름")
    arguments: Optional[dict] = Field(None, description="실행 인자")


class MCPRunResponse(BaseModel):
    """MCP 실행 응답 스키마
    
    GET /api/mcp/runs/{runld} 응답 시 사용
    """
    id: int
    session_id: int
    status: str = Field(
        ...,
        description="실행 상태",
        examples=["pending", "running", "completed", "failed", "cancelled"]
    )
    result: Optional[dict[str, Any]] = Field(None, description="실행 결과")
    arguments: Optional[dict] = Field(None, description="실행 인자")
    progress: Optional[float] = Field(None, description="진행률 (0-1)")
    message: Optional[str] = Field(None, description="상태 메시지")
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class MCPRunStatusResponse(BaseModel):
    """MCP 실행 상태 응답 스키마
    
    GET /api/mcp/runs/{runld} 상태 조회 시 사용
    """
    id: int
    status: str
    progress: Optional[float] = Field(None, description="진행률 (0-1)")
    message: Optional[str] = Field(None, description="상태 메시지")
    result: Optional[dict[str, Any]] = Field(None, description="현재까지의 결과")


class MCPRunListResponse(BaseModel):
    """MCP 실행 목록 응답 스키마"""
    items: List[MCPRunResponse]
    total: int


class MCPProjectStatusResponse(BaseModel):
    """프로젝트별 MCP 상태 응답 스키마"""

    id: str = Field(..., description="프로젝트 ID")
    name: str = Field(..., description="프로젝트 이름")
    mcp_status: Optional[str] = Field(
        None,
        alias="mcpStatus",
        description="MCP 연결 상태 (connected, pending, null)",
        examples=["connected", "pending", None],
    )

    model_config = ConfigDict(populate_by_name=True)

