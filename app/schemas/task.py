"""Task-related Pydantic schemas."""

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TaskBase(BaseModel):
    """태스크 기본 스키마"""

    title: str = Field(..., description="태스크 제목", max_length=500)
    description: str | None = Field(None, description="태스크 설명")
    description_md: str | None = Field(None, description="태스크 설명 마크다운")
    type: str = Field(
        default="feat",
        description="태스크 타입",
        examples=["feat", "bug", "docs", "design", "refactor"],
    )
    source: str = Field(default="USER", description="태스크 생성 소스", examples=["MCP", "USER", "AI"])
    status: str = Field(
        default="todo",
        description="태스크 상태",
        examples=["todo", "in_progress", "review", "done"],
    )
    priority: int = Field(default=5, description="우선순위 (0-10)", ge=0, le=10)
    tags: list[str] | None = Field(None, description="태그 목록")
    due_at: datetime | None = Field(None, description="마감일")


class TaskInsightRequest(BaseModel):
    project_id: int


class TaskInsightResponse(BaseModel):
    task_completed_probability: float
    task_last_updated: datetime | None
    QA_test: int | None


class TaskCreate(TaskBase):
    """태스크 생성 요청 스키마

    POST /api/v1/projects/{projectId}/tasks 요청 시 사용
    """

    pass


class TaskUpdate(BaseModel):
    """태스크 수정 요청 스키마

    PATCH /api/v1/tasks/{taskId} 요청 시 사용
    """

    title: str | None = Field(None, description="태스크 제목", max_length=500)
    description: str | None = Field(None, description="태스크 설명")
    description_md: str | None = Field(None, description="태스크 설명 마크다운")
    type: str | None = Field(None, description="태스크 타입")
    status: str | None = Field(None, description="태스크 상태")
    priority: int | None = Field(None, description="우선순위 (0-10)", ge=0, le=10)
    tags: list[str] | None = Field(None, description="태그 목록")
    due_at: datetime | None = Field(None, description="마감일")
    result_files: list[str] | None = Field(None, description="생성/수정된 파일 목록")
    summary: str | None = Field(None, description="작업 요약")
    duration: int | None = Field(None, description="작업 소요 시간 (초 단위)", ge=0)
    result_logs: str | None = Field(None, description="결과 로그 (마크다운 형식)")


class TaskResponse(TaskBase):
    """태스크 응답 스키마

    GET /api/v1/tasks/{taskId} 응답 시 사용
    """

    id: int
    project_id: int
    result_files: list[str] | None = Field(None, description="생성/수정된 파일 목록")
    summary: str | None = Field(None, description="작업 요약")
    duration: int | None = Field(None, description="작업 소요 시간 (초 단위)")
    result_logs: str | None = Field(None, description="결과 로그 (마크다운 형식)")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_with_json(cls, obj: Any) -> "TaskResponse":
        """ORM 객체에서 JSON 필드를 파싱하여 TaskResponse 생성"""
        data = {
            "id": obj.id,
            "project_id": obj.project_id,
            "title": obj.title,
            "description": obj.description,
            "description_md": obj.description_md,
            "type": obj.type,
            "source": obj.source,
            "status": obj.status,
            "priority": obj.priority,
            "due_at": obj.due_at,
            "summary": obj.summary,
            "duration": obj.duration,
            "result_logs": obj.result_logs,
            "created_at": obj.created_at,
            "updated_at": obj.updated_at,
        }

        # JSON 필드 파싱
        if obj.tags:
            try:
                data["tags"] = json.loads(obj.tags) if isinstance(obj.tags, str) else obj.tags
            except (json.JSONDecodeError, TypeError):
                data["tags"] = []
        else:
            data["tags"] = []

        if obj.result_files:
            try:
                data["result_files"] = json.loads(obj.result_files) if isinstance(obj.result_files, str) else obj.result_files
            except (json.JSONDecodeError, TypeError):
                data["result_files"] = []
        else:
            data["result_files"] = []

        return cls(**data)


class TaskListMeta(BaseModel):
    """태스크 목록 메타 정보"""

    page: int = Field(..., description="현재 페이지")
    page_size: int = Field(..., description="페이지 크기")
    total: int = Field(..., description="전체 태스크 수")

    model_config = ConfigDict(populate_by_name=True)


class TaskListResponse(BaseModel):
    """태스크 목록 응답 스키마

    GET /api/v1/projects/{projectId}/tasks 응답 시 사용
    API 스펙에 맞게 data/meta 형식으로 래핑
    """

    data: list[TaskResponse] = Field(..., description="태스크 목록")
    meta: TaskListMeta = Field(..., description="페이지네이션 메타 정보")

    model_config = ConfigDict(populate_by_name=True)


class TaskDetailResponse(BaseModel):
    """태스크 상세 응답 스키마

    GET /api/v1/tasks/{taskId} 응답 시 사용
    API 스펙에 맞게 data로 래핑
    """

    data: TaskResponse = Field(..., description="태스크 상세 정보")


class TaskDeleteResponse(BaseModel):
    """태스크 삭제 응답 스키마

    DELETE /api/v1/tasks/{taskId} 응답 시 사용
    API 스펙에 맞게 data로 래핑
    """

    data: dict = Field(..., description="삭제 결과")

    @classmethod
    def create(cls, task_id: int) -> "TaskDeleteResponse":
        """삭제 응답 생성"""
        return cls(data={"deleted": True, "id": task_id})


class TaskLinkCreate(BaseModel):
    """태스크 링크 생성 요청 스키마

    POST /api/v1/tasks/links 요청 시 사용
    """

    parent_task_id: int = Field(..., description="부모 태스크 ID")
    child_task_id: int = Field(..., description="자식 태스크 ID")
    link_type: str = Field(..., description="링크 타입", examples=["blocks", "depends_on", "relates_to"])


class TaskLinkResponse(BaseModel):
    """태스크 링크 응답 스키마"""

    id: int
    parent_task_id: int
    child_task_id: int
    link_type: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
