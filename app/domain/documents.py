import traceback

from fastapi import HTTPException
from sqlalchemy.exc import NoResultFound, SQLAlchemyError, IntegrityError
from sqlalchemy.orm import Session
from starlette import status

from app.db.models import Document
from app.schemas.document import DocumentCreateRequest, DocumentUpdateRequest, DocumentPage, DocumentRead


def create_document_service(projectID: int, user_id: str, request: DocumentCreateRequest, db: Session) -> Document:
    project = get_project_by_id(projectID, user_id, db)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project with ID {projectID} not found")

    existing = check_document_exist(projectID, user_id, request, db)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document already exists"
        )

    try:
        document = create_new_document_repo(projectID, user_id, request,  db)
        db.commit()
        db.refresh(document)
        return document

    except NoResultFound:
        raise HTTPException(
            status_code=404,
            detail=f"Project with ID {projectID} not found"
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document already exists"
        )
    except SQLAlchemyError as e:
        db.rollback()
        print("DB Error:", e)
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="database error"
        )

def get_document_service(projectID: int, type: str, user_id: str, db: Session) -> Document:
    try:
        document = get_document_by_id(projectID, type, user_id, db)
        return document
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

def update_project_service(projectID: int, type: str, user_id: str, request: DocumentUpdateRequest, db: Session) -> Document:
    try:
        document = update_document_repo(projectID, type, user_id, request, db)
        db.commit()
        db.refresh(document)
        return document
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

def get_document_list_service(projectID: int, user_id:str, db: Session) -> DocumentPage:
    try:
        documents_orm = get_document_list_repo(projectID, user_id, db)
        return DocumentPage(
            documents=[DocumentRead.model_validate(p) for p in documents_orm]
        )

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



