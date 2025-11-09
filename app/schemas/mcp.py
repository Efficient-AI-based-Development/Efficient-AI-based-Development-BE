"""MCP (Model Context Protocol) related Pydantic schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------


class MCPConnectionCreate(BaseModel):
    provider_id: str = Field(..., alias="providerId", description="연결할 MCP 제공자 ID")
    project_id: str = Field(..., alias="projectId", description="프로젝트 ID(문자열)")
    config: Optional[Dict[str, Any]] = Field(default=None, description="연결 설정 값")
    env: Optional[Dict[str, Any]] = Field(default=None, description="환경 변수")

    model_config = ConfigDict(populate_by_name=True)


class MCPConnectionData(BaseModel):
    connection_id: str = Field(..., alias="connectionId")
    provider_id: str = Field(..., alias="providerId")
    status: str
    created_at: datetime = Field(..., alias="createdAt")
    config: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(populate_by_name=True)


class MCPConnectionResponse(BaseModel):
    data: MCPConnectionData


class MCPConnectionListResponse(BaseModel):
    data: List[MCPConnectionData]


class MCPConnectionCloseResponse(BaseModel):
    data: Dict[str, Any]


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------


class MCPSessionCreate(BaseModel):
    connection_id: str = Field(..., alias="connectionId")
    project_id: str = Field(..., alias="projectId")
    metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(populate_by_name=True)


class MCPSessionData(BaseModel):
    session_id: str = Field(..., alias="sessionId")
    connection_id: str = Field(..., alias="connectionId")
    status: str
    created_at: datetime = Field(..., alias="createdAt")
    metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(populate_by_name=True)


class MCPSessionResponse(BaseModel):
    data: MCPSessionData


class MCPSessionListResponse(BaseModel):
    data: List[MCPSessionData]


class MCPSessionCloseResponse(BaseModel):
    data: Dict[str, Any]


# ---------------------------------------------------------------------------
# Catalog (Tools / Resources / Prompts)
# ---------------------------------------------------------------------------


class MCPToolItem(BaseModel):
    tool_id: str = Field(..., alias="toolId")
    name: str
    description: Optional[str] = None
    input_schema: Optional[Dict[str, Any]] = Field(default=None, alias="inputSchema")
    output_schema: Optional[Dict[str, Any]] = Field(default=None, alias="outputSchema")

    model_config = ConfigDict(populate_by_name=True)


class MCPToolListResponse(BaseModel):
    data: List[MCPToolItem]


class MCPResourceItem(BaseModel):
    uri: str
    kind: str
    description: Optional[str] = None


class MCPResourceListResponse(BaseModel):
    data: List[MCPResourceItem]


class MCPPromptItem(BaseModel):
    prompt_id: str = Field(..., alias="promptId")
    name: str
    description: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class MCPPromptListResponse(BaseModel):
    data: List[MCPPromptItem]


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------


class MCPRunCreate(BaseModel):
    session_id: str = Field(..., alias="sessionId")
    mode: str = Field("chat", description="실행 모드 (tool/chat/prompt)")
    tool_id: Optional[str] = Field(default=None, alias="toolId")
    prompt_id: Optional[str] = Field(default=None, alias="promptId")
    config: Optional[Dict[str, Any]] = None
    input: Dict[str, Any]

    model_config = ConfigDict(populate_by_name=True)


class MCPRunData(BaseModel):
    run_id: str = Field(..., alias="runId")
    session_id: str = Field(..., alias="sessionId")
    mode: Optional[str] = None
    status: str
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")
    result: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(populate_by_name=True)


class MCPRunResponse(BaseModel):
    data: MCPRunData


class MCPRunStatusData(BaseModel):
    run_id: str = Field(..., alias="runId")
    status: str
    result: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    output: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = Field(default=None, alias="startedAt")
    finished_at: Optional[datetime] = Field(default=None, alias="finishedAt")

    model_config = ConfigDict(populate_by_name=True)


class MCPRunStatusResponse(BaseModel):
    data: MCPRunStatusData


class MCPRunCancelResponse(BaseModel):
    data: Dict[str, Any]


class MCPRunEventsResponse(BaseModel):
    data: List[Dict[str, Any]]


# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------


class MCPProjectStatusItem(BaseModel):
    id: str = Field(..., description="프로젝트 ID")
    name: str = Field(..., description="프로젝트 이름")
    mcp_status: Optional[str] = Field(
        None,
        alias="mcpStatus",
        description="MCP 연결 상태 (connected, pending, null)",
    )

    model_config = ConfigDict(populate_by_name=True)


class MCPProjectStatusResponse(BaseModel):
    data: List[MCPProjectStatusItem]
