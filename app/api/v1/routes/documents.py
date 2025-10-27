"""Document API routes."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.document import (
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse,
    DocumentListResponse,
)

router = APIRouter(prefix="/docs", tags=["documents"])


@router.post("/{doc_id}/rewrite", status_code=200)
def rewrite_document_content(doc_id: int, db: Session = Depends(get_db)):
    """AI로 문서 내용 수정
    
    PATCH /api/docs/{docID}/ai/rewrite
    """
    # TODO: 실제 구현 필요
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/{doc_id}/rewrite/full", status_code=200)
def rewrite_full_document(doc_id: int, db: Session = Depends(get_db)):
    """AI로 문서 전체 수정
    
    PATCH /api/docs/{docID}/ai/rewrite/full
    """
    # TODO: 실제 구현 필요
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{doc_id}", response_model=DocumentResponse)
def get_document(doc_id: int, db: Session = Depends(get_db)):
    """문서 조회
    
    GET /api/docs/{docID}
    """
    # TODO: 실제 구현 필요
    raise HTTPException(status_code=501, detail="Not implemented")


@router.patch("/{doc_id}", response_model=DocumentResponse)
def update_document(
    doc_id: int,
    document: DocumentUpdate,
    db: Session = Depends(get_db)
):
    """문서 수정
    
    PATCH /api/docs/{docID}
    """
    # TODO: 실제 구현 필요
    raise HTTPException(status_code=501, detail="Not implemented")


@router.delete("/{doc_id}", status_code=204)
def delete_document(doc_id: int, db: Session = Depends(get_db)):
    """문서 삭제
    
    DELETE /api/docs/{docID}
    """
    # TODO: 실제 구현 필요
    raise HTTPException(status_code=501, detail="Not implemented")

