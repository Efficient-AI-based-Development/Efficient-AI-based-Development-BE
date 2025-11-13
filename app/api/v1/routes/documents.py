"""Document API routes."""

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.db.database import get_db
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

router = APIRouter(prefix="", tags=["documents"])


@router.post("/projects/{project_id}/", response_model=DocumentRead, status_code=201)
def create_document(
    project_id: int,
    request: DocumentCreateRequest,
    user_id: str = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db),
):
    return create_document_service(project_id=project_id, user_id=user_id, request=request, db=db)


@router.get("/projects/{project_id}/docs/{type}", response_model=DocumentRead, status_code=200)
def get_document(
    project_id: int,
    type: str,
    user_id: str = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db),
):
    return get_document_service(project_id=project_id, type=type, user_id=user_id, db=db)


@router.patch("/projects/{project_id}/docs/{type}", response_model=DocumentRead, status_code=200)
def update_document(
    project_id: int,
    type: str,
    request: DocumentUpdateRequest,
    user_id: str = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db),
):
    return update_project_service(
        project_id=project_id, type=type, user_id=user_id, request=request, db=db
    )


@router.get("/projects/{project_id}/docs", response_model=DocumentPage, status_code=200)
def get_document_list(
    project_id: int, user_id: str = Header(..., alias="X-User-ID"), db: Session = Depends(get_db)
):
    return get_document_list_service(project_id=project_id, user_id=user_id, db=db)
