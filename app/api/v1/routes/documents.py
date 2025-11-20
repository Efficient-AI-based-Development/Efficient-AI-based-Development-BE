"""Document API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User
from app.domain.auth import get_current_user
from app.domain.documents import (
    create_document_service,
    get_document_list_service,
    get_document_service,
    update_project_service,
)
from app.schemas.document import (
    DocumentCreateRequest,
    DocumentPage,
    DocumentRead,
    DocumentUpdateRequest,
)

router = APIRouter(prefix="", tags=["documents"], dependencies=[Depends(get_current_user)])


@router.post("/projects/{project_id}/", response_model=DocumentRead, status_code=201)
def create_document(
    project_id: int,
    request: DocumentCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return create_document_service(project_id=project_id, user_id=current_user.user_id, request=request, db=db)


@router.get("/projects/{project_id}/docs/{type}", response_model=DocumentRead, status_code=200)
def get_document(
    project_id: int,
    type: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_document_service(project_id=project_id, type=type, user_id=current_user.user_id, db=db)


@router.patch("/projects/{project_id}/docs/{type}", response_model=DocumentRead, status_code=200)
def update_document(
    project_id: int,
    type: str,
    request: DocumentUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_project_service(project_id=project_id, type=type, user_id=current_user.user_id, request=request, db=db)


@router.get("/projects/{project_id}/docs", response_model=DocumentPage, status_code=200)
def get_document_list(project_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_document_list_service(project_id=project_id, user_id=current_user.user_id, db=db)
