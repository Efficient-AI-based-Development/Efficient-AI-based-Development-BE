from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User
from app.domain.auth import get_current_user
from app.domain.projects import (
    create_project_service,
    delete_project_service,
    get_pagination_params,
    get_project_list_service,
    get_project_service,
    update_project_service,
)
from app.schemas.project import (
    PaginationParams,
    ProjectCreateRequest,
    ProjectDeleteResponse,
    ProjectPage,
    ProjectRead,
    ProjectUpdateRequest,
)

router = APIRouter(prefix="/projects", tags=["project"], dependencies=[Depends(get_current_user)])


@router.post("", response_model=ProjectRead, status_code=201)
def create_project(
    request: ProjectCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return create_project_service(request, current_user.user_id, db)


@router.get("/{project_id}", response_model=ProjectRead, status_code=200)
def get_project(
    project_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return get_project_service(project_id=project_id, user_id=current_user.user_id, db=db)


@router.get("", response_model=ProjectPage, status_code=200)
def get_project_list(
    params: PaginationParams = Depends(get_pagination_params),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_project_list_service(params, current_user.user_id, db)


@router.patch("/{project_id}", response_model=ProjectRead, status_code=200)
def update_project(
    project_id: int,
    request: ProjectUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_project_service(
        project_id=project_id, user_id=current_user.user_id, request=request, db=db
    )


@router.delete("/{project_id}", response_model=ProjectDeleteResponse, status_code=200)
def delete_project(
    project_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return delete_project_service(project_id=project_id, user_id=current_user.user_id, db=db)
