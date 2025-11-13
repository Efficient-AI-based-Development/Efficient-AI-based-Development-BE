"""Generation job-related Pydantic schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GenJobBase(BaseModel):
    """생성 작업 기본 스키마"""

    job_type: str = Field(
        ...,
        description="작업 타입",
        examples=["code_generation", "document_generation", "test_generation", "refactoring"],
    )


class GenJobCreate(GenJobBase):
    """생성 작업 생성 요청 스키마

    POST /api/v1/mcp/runs 요청 시 사용
    """

    pass


class GenJobResponse(GenJobBase):
    """생성 작업 응답 스키마

    GET /api/v1/mcp/runs/{runld} 응답 시 사용
    """

    id: int
    project_id: int
    status: str = Field(
        ...,
        description="작업 상태",
        examples=["pending", "running", "completed", "failed", "cancelled"],
    )
    result: str | None = Field(None, description="생성 결과")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GenJobStatusResponse(BaseModel):
    """생성 작업 상태 응답 스키마

    GET /api/v1/mcp/runs/{runld} 상태 조회 시 사용
    """

    id: int
    status: str
    progress: float | None = Field(None, description="진행률 (0-1)")
    message: str | None = Field(None, description="상태 메시지")


class GenJobListResponse(BaseModel):
    """생성 작업 목록 응답 스키마"""

    items: list[GenJobResponse]
    total: int = Field(..., description="전체 작업 수")


class GenerationRequest(BaseModel):
    """코드/문서 생성 요청 스키마

    POST /api/v1/projects/{projectId}/generate 요청 시 사용
    """

    prompt: str = Field(..., description="생성 프롬프트")
    context: dict[str, Any] | None = Field(None, description="추가 컨텍스트")
