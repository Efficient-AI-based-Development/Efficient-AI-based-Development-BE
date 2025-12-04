"""Task domain logic (service layer)."""

import json
import traceback
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy.exc import NoResultFound, SQLAlchemyError
from sqlalchemy.orm import Session
from starlette import status

from app.db.models import Document, MCPConnection, MCPRun, MCPSession, Project, Task
from app.domain.mcp import MCPService
from app.schemas.mcp import MCPConnectionCreate, MCPRunCreate, MCPSessionCreate
from app.schemas.task import (
    StartDevelopmentRequest,
    StartDevelopmentResponse,
    TaskDeleteResponse,
    TaskDetailResponse,
    TaskListResponse,
    TaskResponse,
    TaskUpdate,
)

############################ 서비스 정의 ############################


@dataclass
class StartDevelopmentContext:
    """Automatically collected context for a Start Development run."""

    task: Task
    project: Project
    documents: list[Document]
    prd_doc: Document | None
    srs_doc: Document | None
    user_story_docs: list[Document]
    recent_runs: list[MCPRun]


def get_task_service(task_id: int, db: Session) -> TaskDetailResponse:
    """태스크 상세 조회 서비스"""
    try:
        task = get_task_by_id(task_id, db)
        task_response = to_task_response(task)
        return TaskDetailResponse(data=task_response)
    except NoResultFound:
        raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found")
    except SQLAlchemyError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="database error")


def list_tasks_service(project_id: int, db: Session) -> TaskListResponse:
    """태스크 목록 조회 서비스"""
    try:
        # 프로젝트 존재 여부 확인
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail=f"Project with ID {project_id} not found")

        # 페이지네이션 없이 모든 태스크 조회
        tasks_orm = db.query(Task).filter(Task.project_id == project_id).order_by(Task.id.desc()).all()

        tasks: list[TaskResponse] = [to_task_response(t) for t in tasks_orm]

        return TaskListResponse(data=tasks)
    except SQLAlchemyError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="database error")


def update_task_service(task_id: int, request: TaskUpdate, db: Session) -> TaskDetailResponse:
    """태스크 수정 서비스"""
    try:
        task = update_task_repo(task_id, request, db)
        db.commit()
        db.refresh(task)

        task_response = to_task_response(task)
        return TaskDetailResponse(data=task_response)
    except NoResultFound:
        db.rollback()
        raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found")
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="database error")


def delete_task_service(task_id: int, db: Session) -> TaskDeleteResponse:
    """태스크 삭제 서비스"""
    try:
        task = delete_task_repo(task_id, db)
        resp = TaskDeleteResponse.create(task.id)
        db.commit()
        return resp
    except NoResultFound:
        db.rollback()
        raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found")
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="database error")


def start_development_service(task_id: int, request: StartDevelopmentRequest, db: Session) -> StartDevelopmentResponse:
    """Start Development 서비스 - vooster.ai 스타일 플로우"""
    try:
        context = _collect_start_development_context(task_id, db)
        provider_id = request.provider_id or "chatgpt"
        options = request.options or {}

        mcp_service = MCPService(db)
        connection_id = _ensure_active_connection(context.project.id, provider_id, mcp_service, db)

        session_data = mcp_service.create_session(
            MCPSessionCreate(
                connection_id=connection_id,
                project_id=str(context.project.id),
                metadata={
                    "taskId": context.task.id,
                    "taskTitle": context.task.title,
                    "mode": "start_development",
                    "providerId": provider_id,
                },
            )
        )

        prompt = _build_development_prompt(context, options)

        run_data = mcp_service.create_run(
            MCPRunCreate(
                session_id=session_data.session_id,
                mode="chat",
                task_id=context.task.id,
                input={
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an AI assistant helping with software development. Keep outputs actionable and concise.",
                        },
                        {"role": "user", "content": prompt},
                    ]
                },
                config={
                    "model": options.get("model"),
                    "temperature": options.get("temperature", 0.2),
                    "systemPrompt": "You are implementing a software development task. Provide clear, actionable steps.",
                },
            )
        )

        preview = _build_preview_message(context.task)
        summary = _extract_run_summary(run_data.result)
        return StartDevelopmentResponse(
            session_id=session_data.session_id,
            run_id=run_data.run_id,
            status=run_data.status,
            preview=preview,
            summary=summary,
        )

    except NoResultFound:
        db.rollback()
        raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found")
    except Exception as e:
        db.rollback()
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Start Development 실패: {str(e)}",
        )


def _collect_start_development_context(task_id: int, db: Session) -> StartDevelopmentContext:
    """Gather task, project, related docs, and recent AI runs for the Start Development flow."""
    task = get_task_by_id(task_id, db)
    project = db.query(Project).filter(Project.id == task.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project with ID {task.project_id} not found")

    documents = db.query(Document).filter(Document.project_id == project.id).order_by(Document.updated_at.desc()).all()
    prd_doc = next((doc for doc in documents if doc.type == "PRD"), None)
    srs_doc = next((doc for doc in documents if doc.type == "SRS"), None)
    user_story_docs = [doc for doc in documents if doc.type == "USER_STORY"]

    recent_runs = (
        db.query(MCPRun)
        .join(MCPSession, MCPRun.session_id == MCPSession.id)
        .join(MCPConnection, MCPSession.connection_id == MCPConnection.id)
        .filter(MCPRun.task_id == task.id, MCPConnection.project_id == project.id)
        .order_by(MCPRun.created_at.desc())
        .limit(3)
        .all()
    )

    return StartDevelopmentContext(
        task=task,
        project=project,
        documents=documents,
        prd_doc=prd_doc,
        srs_doc=srs_doc,
        user_story_docs=user_story_docs,
        recent_runs=recent_runs,
    )


def _ensure_active_connection(project_id: int, provider_id: str, mcp_service: MCPService, db: Session) -> str:
    """Ensure an active MCP connection exists for the project and provider."""
    connection = (
        db.query(MCPConnection)
        .filter(
            MCPConnection.project_id == project_id,
            MCPConnection.connection_type == provider_id,
        )
        .first()
    )

    if not connection:
        connection_data = mcp_service.create_connection(MCPConnectionCreate(provider_id=provider_id, project_id=str(project_id)))
        connection_id = connection_data.connection_id
        mcp_service.activate_connection(connection_id)
        return connection_id

    connection_id = f"cn_{connection.id:04d}"
    if connection.status != "active":
        mcp_service.activate_connection(connection_id)
    return connection_id


def _build_development_prompt(context: StartDevelopmentContext, options: dict[str, Any]) -> str:
    """Task 기반 개발 프롬프트 생성 (vooster 스타일)."""
    task = context.task
    project = context.project
    mode = (options.get("mode") or "impl").lower()
    mode_hint = {
        "impl": "Implement the task end-to-end.",
        "refactor": "Refactor existing logic without changing behavior.",
        "review": "Review the current state and propose a safe plan.",
    }.get(mode, "Implement the task end-to-end.")

    prompt_parts = [
        f"# Task: {task.title}",
        "",
        "## Mode",
        f"{mode} - {mode_hint}",
        "",
        "## Task Details",
        task.description_md or task.description or "No description provided.",
        "",
        "## Task Meta",
        f"- Type: {task.type}",
        f"- Priority: {task.priority}",
        f"- Status: {task.status}",
        "",
    ]

    if task.summary:
        prompt_parts.extend(["## Task Summary", task.summary, ""])

    if project.content_md:
        prompt_parts.extend(["## Project Overview", _truncate_md(project.content_md), ""])

    if context.prd_doc and context.prd_doc.content_md:
        prompt_parts.extend(
            [
                "## Product Requirements (PRD)",
                _truncate_md(context.prd_doc.content_md),
                "",
            ]
        )

    if context.srs_doc and context.srs_doc.content_md:
        prompt_parts.extend(
            [
                "## Software Requirements (SRS)",
                _truncate_md(context.srs_doc.content_md),
                "",
            ]
        )

    if context.user_story_docs:
        prompt_parts.append("## User Stories")
        for doc in context.user_story_docs[:3]:
            prompt_parts.append(f"- {doc.title}: {_truncate_md(doc.content_md)}")
        prompt_parts.append("")

    if context.recent_runs:
        prompt_parts.append("## Recent AI Runs for this Task")
        for run in context.recent_runs:
            prompt_parts.append(_summarize_recent_run(run))
        prompt_parts.append("")

    prompt_parts.extend(
        [
            "## Output Expectations",
            "- Return a short plan first if substantial work is required.",
            "- Propose code changes with file names and snippets.",
            "- Keep responses concise but specific to this repo.",
        ]
    )

    return "\n".join(prompt_parts)


def _build_preview_message(task: Task) -> str:
    return f"지금부터 Task #{task.id}: {task.title} 작업을 시작합니다."


def _extract_run_summary(result: dict[str, Any] | None) -> str | None:
    """Extract a human-readable summary from a run result payload."""
    if not result:
        return None
    if isinstance(result, dict):
        return result.get("summary") or result.get("outputText") or result.get("output_text") or result.get("message")
    return None


def _truncate_md(content: str | None, limit: int = 1200) -> str:
    """Trim long markdown blobs so prompts stay compact."""
    if not content:
        return ""
    return content[:limit] + ("..." if len(content) > limit else "")


def _summarize_recent_run(run: MCPRun) -> str:
    """Create a single-line summary for a previous run."""
    try:
        payload = json.loads(run.result) if run.result else {}
    except json.JSONDecodeError:
        payload = {}

    output = payload.get("summary") or payload.get("outputText") or payload.get("output_text") or payload.get("message") or ""
    output_preview = output[:140] + ("..." if len(output) > 140 else "")
    timestamp = run.created_at.isoformat() if isinstance(run.created_at, datetime) else ""
    return f"- [{timestamp}] status={run.status} :: {output_preview}"


############################ REPO 관리 ############################


def get_task_by_id(task_id: int, db: Session) -> Task:
    """ID로 태스크 조회"""
    task = db.query(Task).filter(Task.id == task_id).one()
    return task


def get_task_list_repo(project_id: int, q: str | None, page: int, per_page: int, db: Session) -> tuple[list[Task], int]:
    """태스크 목록 조회 레포지토리 (페이지네이션)"""
    query = db.query(Task).filter(Task.project_id == project_id)

    if q:
        query = query.filter(Task.title.ilike(f"%{q}%"))

    total = query.count()

    items = query.order_by(Task.id.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return items, total


def update_task_repo(task_id: int, request: TaskUpdate, db: Session) -> Task:
    """태스크 수정 레포지토리"""
    task = db.query(Task).filter(Task.id == task_id).one()

    data = request.model_dump(exclude_unset=True, exclude_none=True)

    # JSON 필드 처리
    if "tags" in data and data["tags"]:
        data["tags"] = json.dumps(data["tags"], ensure_ascii=False)
    elif "tags" in data and data["tags"] is None:
        data["tags"] = None

    if "result_files" in data and data["result_files"]:
        data["result_files"] = json.dumps(data["result_files"], ensure_ascii=False)
    elif "result_files" in data and data["result_files"] is None:
        data["result_files"] = None

    for k, v in data.items():
        setattr(task, k, v)

    return task


def delete_task_repo(task_id: int, db: Session) -> Task:
    """태스크 삭제 레포지토리"""
    task = db.query(Task).filter(Task.id == task_id).one()
    db.delete(task)
    return task


def to_task_response(task: Task) -> TaskResponse:
    """ORM 객체를 TaskResponse로 변환"""
    return TaskResponse.from_orm_with_json(task)
