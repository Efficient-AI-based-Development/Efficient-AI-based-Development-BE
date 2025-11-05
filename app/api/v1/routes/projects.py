from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.project import ProjectCreateRequest, ProjectUpdateRequest, ProjectRead, ProjectPage, \
    ProjectDeleteResponse

router = APIRouter(prefix="/projects", tags=["project"])


@router.post("", response_model=ProjectRead, status_code=201)
def create_project(request: ProjectCreateRequest, db: Session = Depends(get_db)):
    return create_project_service(request, db)


@router.get("/{projectID}", response_model=ProjectRead, status_code=200)
def get_project(projectID: int, db: Session = Depends(get_db)):
    return get_project_service(projectID, db)


@router.get("", response_model=ProjectPage, status_code=200)
def get_project_list(
    params: PaginationParams = Depends(get_pagination_params), db: Session = Depends(get_db)
):
    return get_project_list_service(params, db)


@router.patch("/{projectID}", response_model=ProjectRead, status_code=200)
def update_project(projectID: int, request: ProjectUpdateRequest, db: Session = Depends(get_db)):
    return update_project_service(projectID, request, db)


@router.delete("/{projectID}", response_model=ProjectDeleteResponse, status_code=200)
def delete_project(projectID: int, db: Session = Depends(get_db)):
    return delete_project_service(projectID, db)
