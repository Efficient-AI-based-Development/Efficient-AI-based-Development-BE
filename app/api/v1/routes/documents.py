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


@router.post("/projects/{projectID}/", response_model=DocumentRead, status_code=201)
def create_document(
    projectID: int,
    request: DocumentCreateRequest,
    user_id: str = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db),
):
    return create_document_service(projectID, user_id, request, db)


@router.get("/projects/{projectID}/docs/{type}", response_model=DocumentRead, status_code=200)
def get_document(
    projectID: int,
    type: str,
    user_id: str = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db),
):
    return get_document_service(projectID, type, user_id, db)


@router.patch("/projects/{projectID}/docs/{type}", response_model=DocumentRead, status_code=200)
def update_document(
    projectID: int,
    type: str,
    request: DocumentUpdateRequest,
    user_id: str = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db),
):
    return update_project_service(projectID, type, user_id, request, db)


@router.get("/projects/{projectID}/docs", response_model=DocumentPage, status_code=200)
def get_document_list(
    projectID: int, user_id: str = Header(..., alias="X-User-ID"), db: Session = Depends(get_db)
):
    return get_document_list_service(projectID, user_id, db)
