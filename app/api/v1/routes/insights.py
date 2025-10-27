"""Insights API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.insight import ProjectInsightsResponse, InsightSummaryResponse

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("/projects/{project_id}/insights", response_model=ProjectInsightsResponse)
def get_project_insights(project_id: int, db: Session = Depends(get_db)):
    """프로젝트 인사이트 조회
    
    GET /api/v1/projects/{project_id}/insights
    """
    # TODO: 실제 구현 필요
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/summary", response_model=InsightSummaryResponse)
def get_insights_summary(db: Session = Depends(get_db)):
    """전체 인사이트 요약 조회
    
    GET /api/v1/insights/summary
    """
    # TODO: 실제 구현 필요
    raise HTTPException(status_code=501, detail="Not implemented")

