"""Task API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.task import (
    TaskCreate,
    TaskListResponse,
    TaskResponse,
    TaskUpdate,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/projects/{project_id}/tasks", response_model=TaskResponse, status_code=201)
def create_task(
    project_id: int,
    task: TaskCreate,
    db: Session = Depends(get_db)
):
    """태스크 생성
    
    POST /api/v1/projects/{project_id}/tasks
    """
    # TODO: 실제 구현 필요
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/projects/{project_id}/tasks", response_model=TaskListResponse)
def list_tasks(project_id: int, db: Session = Depends(get_db)):
    """태스크 목록 조회
    
    GET /api/v1/projects/{project_id}/tasks
    """
    # TODO: 실제 구현 필요
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db)):
    """태스크 조회
    
    GET /api/v1/tasks/{task_id}
    """
    # TODO: 실제 구현 필요
    raise HTTPException(status_code=501, detail="Not implemented")


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    task: TaskUpdate,
    db: Session = Depends(get_db)
):
    """태스크 수정
    
    PATCH /api/v1/tasks/{task_id}
    """
    # TODO: 실제 구현 필요
    raise HTTPException(status_code=501, detail="Not implemented")


@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    """태스크 삭제
    
    DELETE /api/v1/tasks/{task_id}
    """
    # TODO: 실제 구현 필요
    raise HTTPException(status_code=501, detail="Not implemented")

