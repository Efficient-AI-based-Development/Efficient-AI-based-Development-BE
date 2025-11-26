"""Insights API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.domain.auth import get_current_user
from app.domain.insights import task_insights_service
from app.schemas.insight import TaskInsightResponse

router = APIRouter(prefix="/insights", tags=["insights"], dependencies=[Depends(get_current_user)])


@router.get("/projects/{project_id}/insights", response_model=TaskInsightResponse)
def get_project_insights(project_id: int, db: Session = Depends(get_db)):
    return task_insights_service(project_id, db)
