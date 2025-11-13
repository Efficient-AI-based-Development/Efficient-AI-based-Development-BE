"""Project-related Pydantic schemas."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ProjectBase(BaseModel):
    id: int
    project_idx: int
    title: str
    content_md: str | None = None
    content_md_json: dict[str, Any] | None = None
    status: Literal["not_started", "in_progress", "completed"] | None = None
    model_config = ConfigDict(from_attributes=True)


# 요청 DTO
class ProjectCreateRequest(BaseModel):
    title: str
    service_color: str
    page_size: int
    func_cnt: int
    AI_model: str
    tech_stack: str


class ProjectCreateResponse(ProjectBase):
    title: str
    service_color: str
    page_size: int
    func_cnt: int
    AI_model: str
    tech_stack: str


class ProjectUpdateRequest(BaseModel):
    title: str | None = None
    status: Literal["not_started", "in_progress", "completed"] | None = None


# 단일 응답 DTO (공통 응답)
class ProjectRead(ProjectBase):
    owner_id: str
    created_at: datetime
    updated_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


# 목록 응답
class PageMeta(BaseModel):
    page: int
    page_size: int = Field(..., alias="page_size")
    total: int
    model_config = ConfigDict(populate_by_name=True)


class ProjectPage(BaseModel):
    projects: list[ProjectRead]
    meta: PageMeta
    model_config = ConfigDict(populate_by_name=True)


# 삭제 응답
class ProjectDeleteResponse(BaseModel):
    id: int
    project_idx: int
    title: str
    deleted_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PaginationParams(BaseModel):
    q: str | None = None
    page: int = 1
    page_size: int = Field(10, alias="page_size")
    model_config = ConfigDict(populate_by_name=True)
