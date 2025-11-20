"""Task domain logic (service layer)."""

import json
import traceback

from fastapi import HTTPException, Query
from sqlalchemy.exc import IntegrityError, NoResultFound, SQLAlchemyError
from sqlalchemy.orm import Session
from starlette import status

from app.db.models import Project, Task
from app.schemas.project import PaginationParams
from app.schemas.task import (
    TaskCreate,
    TaskDeleteResponse,
    TaskDetailResponse,
    TaskListMeta,
    TaskListResponse,
    TaskResponse,
    TaskUpdate,
)

############################ 서비스 정의 ############################


def create_task_service(project_id: int, request: TaskCreate, db: Session) -> TaskDetailResponse:
    """태스크 생성 서비스"""
    try:
        # 프로젝트 존재 여부 확인
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail=f"Project with ID {project_id} not found")

        task = create_task_repo(project_id, request, db)
        db.commit()
        db.refresh(task)

        task_response = to_task_response(task)
        return TaskDetailResponse(data=task_response)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Task creation failed")
    except SQLAlchemyError as e:
        db.rollback()
        print("DB Error:", e)
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="database error")


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


def list_tasks_service(project_id: int, params: PaginationParams, db: Session) -> TaskListResponse:
    """태스크 목록 조회 서비스 (페이지네이션)"""
    try:
        # 프로젝트 존재 여부 확인
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail=f"Project with ID {project_id} not found")

        q = (params.q or "").strip() or None
        per_page = min(max(10, params.page_size), 50)
        page = max(1, params.page or 1)

        tasks_orm, total = get_task_list_repo(project_id=project_id, q=q, page=page, per_page=per_page, db=db)

        total_pages = max(1, int((total + per_page - 1) / per_page))

        if page > total_pages:
            raise HTTPException(
                status_code=400,
                detail=(f"page는 최대 {total_pages}까지입니다. " f"(total={total}, page_size={params.page_size})",),
            )

        tasks: list[TaskResponse] = [to_task_response(t) for t in tasks_orm]
        meta = TaskListMeta(page=page, page_size=per_page, total=total)

        return TaskListResponse(data=tasks, meta=meta)
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


def get_pagination_params(
    q: str | None = Query(None, description="검색어"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(10, ge=10, le=50, description="페이지 크기"),
) -> PaginationParams:
    """페이지네이션 파라미터 생성"""
    if page > page_size:
        raise HTTPException(
            status_code=400,
            detail=(f"페이지 번호(page)는 페이지 크기(page_size)보다 클 수 없습니다." f" (page={page}, page_size={page_size})",),
        )
    return PaginationParams(q=q, page_size=page_size, page=page)


############################ REPO 관리 ############################


def get_task_by_id(task_id: int, db: Session) -> Task:
    """ID로 태스크 조회"""
    task = db.query(Task).filter(Task.id == task_id).one()
    return task


def create_task_repo(project_id: int, request: TaskCreate, db: Session) -> Task:
    """태스크 생성 레포지토리"""
    data = request.model_dump()

    # JSON 필드 처리
    if "tags" in data and data["tags"]:
        data["tags"] = json.dumps(data["tags"], ensure_ascii=False)
    else:
        data["tags"] = None

    # result_files는 생성 시에는 None
    data.pop("result_files", None)

    task = Task(project_id=project_id, **data)
    db.add(task)
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
