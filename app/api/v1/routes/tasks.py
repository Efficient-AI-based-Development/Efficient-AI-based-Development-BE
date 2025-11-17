"""Task API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.domain.tasks import (
    create_task_service,
    delete_task_service,
    get_pagination_params,
    get_task_service,
    list_tasks_service,
    update_task_service,
)
from app.schemas.task import (
    TaskCreate,
    TaskDeleteResponse,
    TaskDetailResponse,
    TaskListResponse,
    TaskUpdate,
)

router = APIRouter(tags=["tasks"], dependencies=[Depends(get_db)])


@router.post("/projects/{project_id}/tasks", response_model=TaskDetailResponse, status_code=201)
def create_task(project_id: int, task: TaskCreate, db: Session = Depends(get_db)):
    """태스크 생성

    POST /api/v1/projects/{project_id}/tasks

    특정 프로젝트 내 새로운 Task(기능, 버그, 기타) 생성 - AI 또는 사용자가 생성
    """
    return create_task_service(project_id, task, db)


@router.get("/projects/{project_id}/tasks", response_model=TaskListResponse)
def list_tasks(
    project_id: int, params=Depends(get_pagination_params), db: Session = Depends(get_db)
):
    """태스크 목록 조회

    GET /api/v1/projects/{project_id}/tasks

    특정 프로젝트 내 Task 목록 조회 (페이지네이션 지원)
    """
    return list_tasks_service(project_id, params, db)


@router.get("/tasks/{task_id}", response_model=TaskDetailResponse)
def get_task(task_id: int, db: Session = Depends(get_db)):
    """태스크 상세 조회

    GET /api/v1/tasks/{task_id}

    특정 Task 상세 내용 조회
    """
    return get_task_service(task_id, db)


@router.patch("/tasks/{task_id}", response_model=TaskDetailResponse)
def update_task(task_id: int, task: TaskUpdate, db: Session = Depends(get_db)):
    """태스크 수정

    PATCH /api/v1/tasks/{task_id}

    Task 내용 또는 상태 수정
    """
    return update_task_service(task_id, task, db)


@router.delete("/tasks/{task_id}", response_model=TaskDeleteResponse)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    """태스크 삭제

    DELETE /api/v1/tasks/{task_id}

    Task를 영구 삭제
    """
    return delete_task_service(task_id, db)
