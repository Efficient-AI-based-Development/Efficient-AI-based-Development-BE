"""Project API routes."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Project as ProjectModel
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("/", response_model=ProjectResponse, status_code=201)
def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    """프로젝트 생성
    
    POST /api/v1/projects/
    """
    # TODO: 실제 구현 필요
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/", response_model=ProjectListResponse)
def list_projects(q: str = None, page: int = 1, page_size: int = 10, db: Session = Depends(get_db)):
    """프로젝트 목록 조회
    
    GET /api/v1/projects
    - q: 프로젝트 제목 검색
    - page: 페이지 번호
    - page_size: 한 페이지당 항목 수
    """
    # TODO: 실제 구현 필요
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: int, db: Session = Depends(get_db)):
    """프로젝트 조회
    
    GET /api/v1/projects/{project_id}
    """
    # TODO: 실제 구현 필요
    raise HTTPException(status_code=501, detail="Not implemented")


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    project: ProjectUpdate,
    db: Session = Depends(get_db)
):
    """프로젝트 수정
    
    PATCH /api/v1/projects/{project_id}
    """
    # TODO: 실제 구현 필요
    raise HTTPException(status_code=501, detail="Not implemented")


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    """프로젝트 삭제
    
    DELETE /api/v1/projects/{project_id}
    """
    # TODO: 실제 구현 필요
    raise HTTPException(status_code=501, detail="Not implemented")

