import json
import traceback
from datetime import UTC, datetime

from fastapi import HTTPException, Query
from sqlalchemy.exc import IntegrityError, NoResultFound, SQLAlchemyError
from sqlalchemy.orm import Session
from starlette import status

from app.db.models import Project
from app.schemas.project import (
    PageMeta,
    PaginationParams,
    ProjectCreateRequest,
    ProjectDeleteResponse,
    ProjectPage,
    ProjectRead,
    ProjectUpdateRequest,
)


#################################################################################################################################################################
########################################################################### 서비스 정의 ###########################################################################
#################################################################################################################################################################
def get_project_service(project_id: int, db: Session) -> ProjectRead:
    try:
        project = get_project_by_id(project_id, db)
        return to_project_read(project)
    except NoResultFound:
        raise HTTPException(status_code=404, detail=f"Project with ID {project_id} not found")
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="database error"
        )


def create_project_service(request: ProjectCreateRequest, user_id: str, db: Session) -> ProjectRead:
    try:
        project = create_new_project_repo(request, user_id, db)
        db.commit()
        db.refresh(project)
        json_content = json.loads(project.content_md)
        return ProjectRead(**project.__dict__, content_md_json=json_content)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Project already exists")
    except SQLAlchemyError as e:
        db.rollback()
        print("DB Error:", e)
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="database error"
        )


def get_project_list_service(params: PaginationParams, user_id: str, db: Session) -> ProjectPage:
    try:
        q = (params.q or "").strip() or None
        per_page = min(max(10, params.page_size), 50)
        page = max(1, params.page or 1)

        projects_orm, total = get_project_list_repo(
            q=q, page=page, per_page=per_page, user_id=user_id, db=db
        )
        total_pages = max(1, int((total + per_page - 1) / per_page))

        if page > total_pages:
            raise HTTPException(
                status_code=400,
                detail=f"page는 최대 {total_pages}까지입니다. (total={total}, pageSize={params.page_size})",
            )

        projects: list[ProjectRead] = [to_project_read(p) for p in projects_orm]
        meta = PageMeta(page=page, page_size=per_page, total=total)

        return ProjectPage(projects=projects, meta=meta)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="database error"
        )


def to_project_read(project):
    json_content = None
    if project.content_md:
        try:
            json_content = json.loads(project.content_md)
        except:
            json_content = None

    return ProjectRead(**project.__dict__, content_md_json=json_content)


def update_project_service(
    project_id: int, user_id: str, request: ProjectUpdateRequest, db: Session
) -> ProjectRead:
    try:
        project = update_project_repo(project_id, user_id, request, db)
        db.commit()
        db.refresh(project)
        return to_project_read(project)
    except NoResultFound:
        db.rollback()
        raise HTTPException(status_code=404, detail=f"Project with ID {project_id} not found")
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="database error"
        )


def delete_project_service(project_id: int, user_id: str, db: Session) -> ProjectDeleteResponse:
    try:
        project = delete_project_repo(project_id, user_id, db)
        resp = ProjectDeleteResponse(
            id=project.id,
            project_idx=project.project_idx,
            title=project.title,
            deleted_at=datetime.now(UTC),
        )
        db.commit()
        return resp

    except NoResultFound:
        db.rollback()
        raise HTTPException(status_code=404, detail=f"Project with ID {project_id} not found")

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="database error"
        )


def get_pagination_params(
    q: str | None = Query(None, description="검색어"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(10, ge=10, le=50, alias="pageSize", description="페이지 크기"),
) -> PaginationParams:
    if page > page_size:
        raise HTTPException(
            status_code=400,
            detail=f"페이지 번호(page)는 페이지 크기(pageSize)보다 클 수 없습니다. (page={page}, pageSize={page_size})",
        )
    return PaginationParams(q=q, page_size=page_size, page=page)


#################################################################################################################################################################
########################################################################### REPO 관리 ############################################################################
#################################################################################################################################################################
def get_project_by_id(project_id: int, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id).one()
    return project


def create_new_project_repo(request: ProjectCreateRequest, user_id: str, db: Session) -> Project:

    data = request.model_dump()

    content_md = json.dumps(data, ensure_ascii=False, indent=2)

    project = Project(title=data["title"], content_md=content_md, owner_id=user_id)
    db.add(project)
    return project


def get_project_list_repo(
    q: str | None, page: int, per_page: int, user_id: str, db: Session
) -> tuple[list[Project], int]:
    query = db.query(Project).filter(Project.owner_id == user_id)
    if q:
        query = query.filter(Project.title.ilike(f"%{q}%"))

    total = query.count()

    items = query.order_by(Project.id.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return items, total


def update_project_repo(
    project_id: int, user_id: str, request: ProjectUpdateRequest, db: Session
) -> Project:

    project = db.query(Project).filter(Project.owner_id == user_id, Project.id == project_id).one()

    data = request.model_dump(exclude_unset=True, exclude_none=True)

    for k, v in data.items():
        setattr(project, k, v)

    return project


def delete_project_repo(project_id: int, user_id: str, db: Session) -> Project:
    project = db.query(Project).filter(Project.owner_id == user_id, Project.id == project_id).one()
    db.delete(project)
    return project
