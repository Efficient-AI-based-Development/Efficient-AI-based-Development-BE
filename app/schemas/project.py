"""Project-related Pydantic schemas."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class ProjectBase(BaseModel):
    """프로젝트 기본 스키마
    
    공통 필드 정의
    """
    name: str = Field(..., description="프로젝트 이름", max_length=255)
    description: Optional[str] = Field(None, description="프로젝트 설명")
    status: str = Field(
        default="active",
        description="프로젝트 상태",
        examples=["active", "completed", "archived"]
    )


class ProjectCreate(ProjectBase):
    """프로젝트 생성 요청 스키마
    
    POST /api/v1/projects/ 요청 시 사용
    """
    pass


class ProjectUpdate(BaseModel):
    """프로젝트 수정 요청 스키마
    
    PATCH /api/v1/projects/{id} 요청 시 사용
    모든 필드가 선택적
    """
    name: Optional[str] = Field(None, description="프로젝트 이름", max_length=255)
    description: Optional[str] = Field(None, description="프로젝트 설명")
    status: Optional[str] = Field(None, description="프로젝트 상태")


class ProjectResponse(ProjectBase):
    """프로젝트 응답 스키마
    
    GET /api/v1/projects/{id} 응답 시 사용
    """
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ProjectListResponse(BaseModel):
    """프로젝트 목록 응답 스키마
    
    GET /api/v1/projects 응답 시 사용
    """
    items: List[ProjectResponse]
    total: int = Field(..., description="전체 프로젝트 수")
    page: int = Field(..., description="현재 페이지 번호")
    page_size: int = Field(..., description="페이지당 항목 수")

