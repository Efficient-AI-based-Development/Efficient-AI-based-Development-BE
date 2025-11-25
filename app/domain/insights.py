from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models import Project, Task
from app.schemas.insight import TaskInsightResponse


def task_insights_service(project_id: int, db: Session) -> TaskInsightResponse:
    proj = db.query(Project).filter(Project.id == project_id).one_or_none()
    if proj is None:
        raise HTTPException(status_code=404, detail="Project not found")
    tasks = db.query(Task).filter(Task.project_id == project_id).order_by(Task.updated_at.desc()).all()
    if len(tasks) == 0:
        return TaskInsightResponse(task_completed_probability=0, task_last_updated=None, QA_test=None)

    updated_at = tasks[0].updated_at
    tasks_num = len(tasks)
    completed = sum(1 for task in tasks if task.status == "done")
    probability = round((completed / tasks_num * 100), 1)
    return TaskInsightResponse(task_completed_probability=probability, task_last_updated=updated_at, QA_test=0)
