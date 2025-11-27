"""Task-related Pydantic schemas."""

import json
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class TaskBase(BaseModel):
    """태스크 기본 스키마"""

    title: str = Field(..., description="태스크 제목", max_length=500)
    description: str | None = Field(None, description="태스크 설명")
    description_md: str | None = Field(None, description="태스크 설명 마크다운")
    type: str = Field(
        default="dev",
        description="태스크 타입",
        examples=["docs", "design", "dev"],
    )
    assigned_role: Literal["Backend", "Frontend"] | None = Field(
        default=None,
        description="담당 역할",
        examples=["Backend", "Frontend"],
    )
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
    assigned_role: Literal["Backend", "Frontend"] | None = Field(None, description="담당 역할 (Backend/Frontend)")
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
    assigned_role: Literal["Backend", "Frontend"] | None = Field(None, description="담당 역할 (Backend/Frontend)")
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
            "status": obj.status,
            "priority": obj.priority,
            "assigned_role": obj.assigned_role,
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


class TaskListResponse(BaseModel):
    """태스크 목록 응답 스키마

    GET /api/v1/projects/{projectId}/tasks 응답 시 사용
    페이지네이션 없이 전체 목록 반환
    """

    data: list[TaskResponse] = Field(..., description="태스크 목록")

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


class StartDevelopmentRequest(BaseModel):
    """Start Development 요청 스키마"""

    provider_id: str | None = Field(
        None,
        description="MCP 제공자 ID (chatgpt, claude, cursor). 없으면 프로젝트 기본값 사용",
        examples=["chatgpt"],
    )
    options: dict[str, Any] | None = Field(
        None,
        description="실행 옵션 (mode, temperature 등)",
        examples=[{"mode": "impl", "temperature": 0.2}],
    )


class StartDevelopmentResponse(BaseModel):
    """Start Development 응답 스키마"""

    session_id: str = Field(..., description="생성된 세션 ID", examples=["ss_0001"])
    run_id: str = Field(..., description="생성된 실행 ID", examples=["run_0001"])
    status: str = Field(..., description="실행 상태", examples=["running", "succeeded"])
    preview: str | None = Field(None, description="미리보기 메시지")
    summary: str | None = Field(None, description="실행 결과 요약")


class StartDevelopmentCommandResponse(BaseModel):
    """Start Development CLI 명령어 응답"""

    command: str = Field(..., description="터미널에 붙여넣어 실행할 curl 명령어")
    provider_id: str = Field(..., alias="providerId", description="MCP 제공자", examples=["claude"])
    task_id: int = Field(..., alias="taskId", description="태스크 ID")
    project_id: int = Field(..., alias="projectId", description="프로젝트 ID")
    note: str | None = Field(None, description="명령 사용 시 참고할 메모")

    model_config = ConfigDict(populate_by_name=True)
