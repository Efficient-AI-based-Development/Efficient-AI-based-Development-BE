"""Task-related Pydantic schemas."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class TaskBase(BaseModel):
    """태스크 기본 스키마"""
    title: str = Field(..., description="태스크 제목", max_length=500)
    description: Optional[str] = Field(None, description="태스크 설명")
    status: str = Field(
        default="pending",
        description="태스크 상태",
        examples=["pending", "in_progress", "completed", "blocked"]
    )
    priority: str = Field(
        default="medium",
        description="우선순위",
        examples=["low", "medium", "high", "urgent"]
    )


class TaskCreate(TaskBase):
    """태스크 생성 요청 스키마
    
    POST /api/v1/projects/{projectId}/tasks 요청 시 사용
    """
    pass


class TaskUpdate(BaseModel):
    """태스크 수정 요청 스키마
    
    PATCH /api/v1/tasks/{taskId} 요청 시 사용
    """
    title: Optional[str] = Field(None, description="태스크 제목", max_length=500)
    description: Optional[str] = Field(None, description="태스크 설명")
    status: Optional[str] = Field(None, description="태스크 상태")
    priority: Optional[str] = Field(None, description="우선순위")


class TaskResponse(TaskBase):
    """태스크 응답 스키마
    
    GET /api/v1/tasks/{taskId} 응답 시 사용
    """
    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class TaskListResponse(BaseModel):
    """태스크 목록 응답 스키마
    
    GET /api/v1/projects/{projectId}/tasks 응답 시 사용
    """
    items: List[TaskResponse]
    total: int = Field(..., description="전체 태스크 수")


class TaskLinkCreate(BaseModel):
    """태스크 링크 생성 요청 스키마
    
    POST /api/v1/tasks/links 요청 시 사용
    """
    parent_task_id: int = Field(..., description="부모 태스크 ID")
    child_task_id: int = Field(..., description="자식 태스크 ID")
    link_type: str = Field(
        ...,
        description="링크 타입",
        examples=["blocks", "depends_on", "relates_to"]
    )


class TaskLinkResponse(BaseModel):
    """태스크 링크 응답 스키마"""
    id: int
    parent_task_id: int
    child_task_id: int
    link_type: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

