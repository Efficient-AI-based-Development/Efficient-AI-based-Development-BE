# app/api/schemas.py

from typing import Any, Literal

from pydantic import BaseModel, Field


# 프로젝트 입력
class ProjectInput(BaseModel):
    user_input: str = Field(..., description="프로젝트 개요/요구사항 자연어 입력")


# PRD
class PRDOutput(BaseModel):
    prd_document: str
    message: str = Field(
        ...,
        description="사용자에게 결과를 안내하는 한국어 메시지 (1~2문장 이상, null 불가)",
    )


# SRS
class SRSOutput(BaseModel):
    srs_document: str
    message: str = Field(
        ...,
        description="사용자에게 결과를 안내하는 한국어 메시지 (1~2문장 이상, null 불가)",
    )


class SRSInput(BaseModel):
    user_input: str = Field(
        ...,
        description="SRS 생성에 사용할 요구사항/설명 자연어 입력",
    )


# User Story
class UserStoryOutput(BaseModel):
    user_story: str
    message: str = Field(
        ...,
        description="사용자에게 결과를 안내하는 한국어 메시지 (1~2문장 이상, null 불가)",
    )


class UserStoryInput(BaseModel):
    user_input: str = Field(
        ...,
        description="User Story 생성에 사용할 요구사항/설명 자연어 입력",
    )


# Task List
class TaskListInput(BaseModel):
    prd_document: str | None = None
    user_input: str | None = None


class Task(BaseModel):
    task_id: int
    title: str
    description: str
    assigned_role: Literal["Backend", "Frontend"]
    priority: int = Field(..., ge=0, le=10)
    tag: Literal["개발", "디자인", "문서"]


class TaskListOutput(BaseModel):
    project_name: str
    tasks: list[Task]


# Planner / SubTask
class SubTask(BaseModel):
    subtask_id: str
    title: str
    description: str
    assigned_role: Literal["Backend", "Frontend"]
    dependencies: list[str] = Field(default_factory=list)


class WriterOutput(BaseModel):
    parent_task_id: str
    srs_document: str


class AuditorOutput(BaseModel):
    next_action: Literal["REFINEMENT", "PASS"]
    feedback: str
    subtasks_review: list[dict[str, Any]] = Field(default_factory=list)


class PlannerOutput(BaseModel):
    parent_task_id: str
    analysis: str
    subtasks: list[SubTask] = Field(default_factory=list)


# Decomposition
class DecompositionInput(BaseModel):
    tasks: list[Task]


class SubTaskWithParent(SubTask):
    parent_task_id: int


class DecompositionItem(BaseModel):
    task_id: int
    title: str
    assigned_role: Literal["Backend", "Frontend"]
    subtasks: list[SubTaskWithParent]
    srs_document: str | None = None


class DecompositionOutput(BaseModel):
    items: list[DecompositionItem]
    all_subtasks: list[SubTaskWithParent]


# Codegen / Repo 스냅샷
class CodeChange(BaseModel):
    file_path: str
    action: Literal["create", "update", "delete"]
    content: str | None = None


class CodegenOutput(BaseModel):
    subtask_id: str
    subtask_title: str
    assigned_role: Literal["Backend", "Frontend"]
    summary: str
    changes: list[CodeChange] = Field(default_factory=list)
    notes: str | None = None
    message: str | None = None


class RepoFile(BaseModel):
    path: str
    content: str


class RepoSnapshot(BaseModel):
    root: str | None = None
    branch: str | None = None
    commit: str | None = None
    files: list[RepoFile] = Field(default_factory=list)
