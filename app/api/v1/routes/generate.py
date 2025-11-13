"""Generation API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.generation import GenerationRequest, GenJobResponse

router = APIRouter(tags=["generation"])


@router.post("/projects/{project_id}/generate", response_model=GenJobResponse, status_code=201)
def create_generation_job(
    project_id: int, request: GenerationRequest, db: Session = Depends(get_db)
):
    """AI 생성 작업 시작

    POST /api/v1/projects/{project_id}/generate
    """
    # TODO: 실제 구현 필요
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/gen-jobs/{job_id}", response_model=GenJobResponse)
def get_generation_job(job_id: int, db: Session = Depends(get_db)):
    """생성 작업 상태 조회

    GET /api/v1/gen-jobs/{job_id}
    """
    # TODO: 실제 구현 필요
    raise HTTPException(status_code=501, detail="Not implemented")
