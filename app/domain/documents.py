import traceback

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError, NoResultFound, SQLAlchemyError
from sqlalchemy.orm import Session
from starlette import status

from app.db.models import Document, Project
from app.schemas.document import (
    DocumentCreateRequest,
    DocumentPage,
    DocumentRead,
    DocumentUpdateRequest,
)

######################### 서비스 정의 #########################


def create_document_service(
    project_id: int, user_id: str, request: DocumentCreateRequest, db: Session
) -> Document:
    project = get_project_by_id(project_id, user_id, db)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project with ID {project_id} not found")

    existing = check_document_exist(project_id, user_id, request, db)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Document already exists")

    try:
        document = create_new_document_repo(project_id, user_id, request, db)
        db.commit()
        db.refresh(document)
        return document

    except NoResultFound:
        raise HTTPException(status_code=404, detail=f"Project with ID {project_id} not found")
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Document already exists")
    except SQLAlchemyError as e:
        db.rollback()
        print("DB Error:", e)
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="database error"
        )


def get_document_service(project_id: int, type: str, user_id: str, db: Session) -> Document:
    try:
        document = get_document(project_id, type, user_id, db)
        return document
    except NoResultFound:
        raise HTTPException(status_code=404, detail=f"Project with ID {project_id} not found")
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="database error"
        )


def update_project_service(
    project_id: int, type: str, user_id: str, request: DocumentUpdateRequest, db: Session
) -> Document:
    try:
        document = update_document_repo(project_id, type, user_id, request, db)
        db.commit()
        db.refresh(document)
        return document
    except NoResultFound:
        db.rollback()
        raise HTTPException(status_code=404, detail=f"Project with ID {project_id} not found")
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="database error"
        )


def get_document_list_service(project_id: int, user_id: str, db: Session) -> DocumentPage:
    try:
        documents_orm = get_document_list_repo(project_id, user_id, db)
        return DocumentPage(documents=[DocumentRead.model_validate(p) for p in documents_orm])

    except NoResultFound:
        raise HTTPException(status_code=404, detail=f"Project with ID {project_id} not found")

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="database error"
        )


######################## REPO 정의 ########################


def check_document_exist(
    project_id: int, user_id: str, request: DocumentCreateRequest, db: Session
) -> Document | None:
    return (
        db.query(Document)
        .filter(
            Document.author_id == user_id,
            Document.project_id == project_id,
            Document.type == request.type,
        )
        .one_or_none()
    )


def get_project_by_id(project_id: int, user_id: str, db: Session) -> Project | None:
    return (
        db.query(Project)
        .filter(Project.owner_id == user_id, Project.id == project_id)
        .one_or_none()
    )


def create_new_document_repo(
    project_id: int, user_id: str, request: DocumentCreateRequest, db: Session
) -> Document:
    # 프로젝트 존재 검사
    data = request.model_dump()
    data["project_id"] = project_id
    data["author_id"] = user_id
    data["last_editor_id"] = user_id
    document = Document(**data)
    db.add(document)
    db.flush()
    return document


def get_document(project_id: int, type: str, user_id: str, db: Session) -> Document:
    document = (
        db.query(Document)
        .filter(
            Document.author_id == user_id, Document.project_id == project_id, Document.type == type
        )
        .one()
    )
    return document


def update_document_repo(
    project_id: int, type: str, user_id: str, request: DocumentUpdateRequest, db: Session
) -> Document:
    document = (
        db.query(Document)
        .filter(
            Document.author_id == user_id, Document.project_id == project_id, Document.type == type
        )
        .one()
    )
    data = request.model_dump(exclude_unset=True, exclude_none=True)

    for k, v in data.items():
        setattr(document, k, v)

    return document


def get_document_list_repo(project_id: int, user_id: str, db: Session) -> list[Document]:
    return (
        db.query(Document)
        .filter(Document.author_id == user_id, Document.project_id == project_id)
        .all()
    )
