"""Insight-related Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel


class TaskInsightRequest(BaseModel):
    project_id: int


class TaskInsightResponse(BaseModel):
    task_completed_probability: float
    task_last_updated: datetime | None
    QA_test: int | None
