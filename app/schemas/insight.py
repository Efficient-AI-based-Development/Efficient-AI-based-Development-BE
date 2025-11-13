"""Insight-related Pydantic schemas."""

from typing import Any

from pydantic import BaseModel, Field


class ProjectInsightsResponse(BaseModel):
    """프로젝트 인사이트 응답 스키마
    
    GET /api/v1/projects/{projectID}/insights 응답 시 사용
    """
    total_tasks: int = Field(..., description="전체 태스크 수")
    completed_tasks: int = Field(..., description="완료된 태스크 수")
    active_tasks: int = Field(..., description="진행 중인 태스크 수")
    pending_tasks: int = Field(..., description="대기 중인 태스크 수")
    total_documents: int = Field(..., description="전체 문서 수")
    recent_activities: list[Any] | None = Field(None, description="최근 활동 목록")


class InsightSummaryResponse(BaseModel):
    """전체 인사이트 요약 응답 스키마
    
    GET /api/v1/insights/summary 응답 시 사용
    """
    total_projects: int = Field(..., description="전체 프로젝트 수")
    active_projects: int = Field(..., description="활성 프로젝트 수")
    total_tasks: int = Field(..., description="전체 태스크 수")
    total_documents: int = Field(..., description="전체 문서 수")
    completed_jobs_today: int = Field(..., description="오늘 완료된 작업 수")

