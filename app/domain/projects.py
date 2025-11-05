import traceback
from typing import List

from fastapi import HTTPException, Query
from sqlalchemy.exc import NoResultFound, SQLAlchemyError, IntegrityError
from sqlalchemy.orm import Session
from starlette import status

from app.db.models import Project
from app.schemas.project import ProjectCreateRequest, ProjectPage, ProjectRead, PageMeta, ProjectUpdateRequest, \
    ProjectDeleteResponse, PaginationParams


############### 서비스 정의 ###############
def get_project_service(projectID: int, db: Session) -> Project:
    try:
        project = repo.get_project_by_id(projectID, db)
        return project
    except NoResultFound:
        raise HTTPException(
            status_code=404,
            detail=f"Project with ID {projectID} not found"
        )
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="database error"
        )

def create_project_service(request: ProjectCreateRequest, db: Session) -> Project:
    try:
        project = repo.create_new_project_repo(request, db)
        db.commit()
        db.refresh(project)
        return project
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Project already exists"
        )
    except SQLAlchemyError as e:
        db.rollback()
        print("DB Error:", e)
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="database error"
        )

def get_project_list_service(params: PaginationParams, db: Session) -> ProjectPage:
    try:
        q = (params.q or "").strip() or None
        per_page = min(max(10, params.pageSize), 50)
        page = max(1, params.page or 1)


        projects_orm, total = repo.get_project_list_repo(q=q, page=page, per_page=per_page, db = db)
        total_pages = max(1, int((total + per_page - 1) / per_page))

        if page > total_pages:
            raise HTTPException(
                status_code=400,
                detail=f"page는 최대 {total_pages}까지입니다. (total={total}, pageSize={params.pageSize})"
            )

        projects: List[ProjectRead] = [ProjectRead.model_validate(p) for p in projects_orm]
        meta = PageMeta(page=page, pageSize=per_page, total=total)

        return ProjectPage(projects=projects, meta=meta)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="database error"
        )

def update_project_service(projectID: int, request: ProjectUpdateRequest, db: Session) -> Project:
    try:
        project = repo.update_project_repo(projectID, request, db)
        db.commit()
        db.refresh(project)
        return project
    except NoResultFound:
        db.rollback()
        raise HTTPException(
            status_code=404,
            detail=f"Project with ID {projectID} not found"
        )
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="database error"
        )

def delete_project_service(projectID: int, db: Session) -> ProjectDeleteResponse:
    try:
        project, delete_time = repo.delete_project_repo(projectID, db)

        db.commit()

        deleted_project = ProjectDeleteResponse(id = project.id, title = project.title, deleted_at = delete_time)

        return deleted_project

    except NoResultFound:
        db.rollback()
        raise HTTPException(
            status_code=404,
            detail=f"Project with ID {projectID} not found"
        )

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="database error"
        )


def get_pagination_params(
    q: str | None = Query(None, description="검색어"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    pageSize: int = Query(10, ge=10, le=50, description="페이지 크기"),
) -> PaginationParams:
    if page > pageSize:
        raise HTTPException(
            status_code=400,
            detail=f"페이지 번호(page)는 페이지 크기(pageSize)보다 클 수 없습니다. (page={page}, pageSize={pageSize})"
        )
    return PaginationParams(q=q, pageSize=pageSize, page=page)
