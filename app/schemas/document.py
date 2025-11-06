"""Document-related Pydantic schemas."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class DocumentBase(BaseModel):
    """문서 기본 스키마"""
    title: str = Field(..., description="문서 제목", max_length=500)
    content: Optional[str] = Field(None, description="문서 내용")
    doc_type: str = Field(
        ...,
        description="문서 타입",
        examples=["PRD", "UserStory", "SRS"]
    )


class DocumentCreate(DocumentBase):
    """문서 생성 요청 스키마

    POST /api/v1/projects/{project_id}/docs 요청 시 사용
    """
    pass


class DocumentUpdate(BaseModel):
    """문서 수정 요청 스키마

    PATCH /api/v1/docs/{docID} 요청 시 사용
    """
    title: Optional[str] = Field(None, description="문서 제목", max_length=500)
    content: Optional[str] = Field(None, description="문서 내용")
    doc_type: Optional[str] = Field(None, description="문서 타입")


class DocumentResponse(DocumentBase):
    """문서 응답 스키마

    GET /api/v1/docs/{docID} 응답 시 사용
    """
    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentListResponse(BaseModel):
    """문서 목록 응답 스키마

    GET /api/v1/projects/{projectID}/docs/ 응답 시 사용
    """
    items: List[DocumentResponse]
    total: int = Field(..., description="전체 문서 수")


class DocumentVersionResponse(BaseModel):
    """문서 버전 응답 스키마

    GET /api/v1/document-versions/{id} 응답 시 사용
    """
    id: int
    document_id: int
    version_number: int
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

