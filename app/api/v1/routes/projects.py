from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Project
from app.domain.projects import create_project_service, get_project_service, get_project_list_service, \
    update_project_service, delete_project_service, get_pagination_params
from app.schemas.project import ProjectCreateRequest, ProjectUpdateRequest, ProjectRead, ProjectPage, \
    ProjectDeleteResponse, PaginationParams, ProjectCreateResponse

router = APIRouter(prefix="/projects", tags=["project"])


@router.post("", response_model=ProjectRead, status_code=201)
def create_project(request: ProjectCreateRequest, user_id: str = Header(..., alias = "X-User-ID"), db: Session = Depends(get_db)):
    return create_project_service(request, user_id, db)


@router.get("/{projectID}", response_model=ProjectRead, status_code=200)
def get_project(projectID: int, db: Session = Depends(get_db)):
    return get_project_service(projectID, db)


@router.get("", response_model=ProjectPage, status_code=200)
def get_project_list(
    params: PaginationParams = Depends(get_pagination_params), user_id: str = Header(..., alias = "X-User-ID"), db: Session = Depends(get_db)
):
    return get_project_list_service(params, user_id, db)


@router.patch("/{projectID}", response_model=ProjectRead, status_code=200)
def update_project(projectID: int, request: ProjectUpdateRequest, user_id: str = Header(..., alias = "X-User-ID"), db: Session = Depends(get_db)):
    return update_project_service(projectID, request, user_id, db)


@router.delete("/{projectID}", response_model=ProjectDeleteResponse, status_code=200)
def delete_project(projectID: int, user_id: str = Header(..., alias = "X-User-ID"),db: Session = Depends(get_db)):
    return delete_project_service(projectID, user_id, db)

