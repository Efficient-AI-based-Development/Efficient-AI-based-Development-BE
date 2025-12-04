"""Task API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.domain.auth import get_current_user
from app.domain.tasks import (
    delete_task_service,
    get_task_service,
    list_tasks_service,
    start_development_service,
    update_task_service,
)
from app.schemas.task import (
    StartDevelopmentRequest,
    StartDevelopmentResponse,
    TaskDeleteResponse,
    TaskDetailResponse,
    TaskListResponse,
    TaskUpdate,
)

router = APIRouter(tags=["tasks"], dependencies=[Depends(get_current_user)])


@router.get("/projects/{project_id}/tasks", response_model=TaskListResponse)
def list_tasks(project_id: int, db: Session = Depends(get_db)):
    """태스크 목록 조회

    GET /api/v1/projects/{project_id}/tasks

    특정 프로젝트 내 Task 전체 목록 조회 (페이지네이션 없음)
    예시 응답:
    ```json
    {
      "data": [
        { "id": 3, "title": "로그인 페이지 구현", "type": "dev", "status": "todo", ... },
        { "id": 2, "title": "PRD 작성", "type": "docs", "status": "done", ... }
      ]
    }
    ```
    """
    return list_tasks_service(project_id, db)


@router.get("/tasks/{task_id}", response_model=TaskDetailResponse)
def get_task(task_id: int, db: Session = Depends(get_db)):
    """태스크 상세 조회

    GET /api/v1/tasks/{task_id}

    특정 Task 상세 내용 조회
    """
    return get_task_service(task_id, db)


@router.patch("/tasks/{task_id}", response_model=TaskDetailResponse)
def update_task(task_id: int, task: TaskUpdate, db: Session = Depends(get_db)):
    """태스크 수정

    PATCH /api/v1/tasks/{task_id}

    Task 내용 또는 상태 수정
    """
    return update_task_service(task_id, task, db)


@router.delete("/tasks/{task_id}", response_model=TaskDeleteResponse)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    """태스크 삭제

    DELETE /api/v1/tasks/{task_id}

    Task를 영구 삭제
    """
    return delete_task_service(task_id, db)


@router.post("/tasks/{task_id}/start-development", response_model=StartDevelopmentResponse, status_code=201)
def start_development(task_id: int, request: StartDevelopmentRequest, db: Session = Depends(get_db)):
    """Start Development - vooster.ai 스타일 개발 시작

    POST /api/v1/tasks/{task_id}/start-development

    Task 정보를 자동으로 수집하여 MCP 세션을 생성하고 개발을 시작합니다.

    ### 동작 흐름:
    1. Task 및 관련 문서(PRD, SRS) 정보 수집
    2. MCP 연결 생성/활성화 (없으면 자동 생성)
    3. MCP 세션 생성
    4. Task 기반 프롬프트 생성
    5. MCP run 생성 및 실행

    ### Request Body:
    - `providerId` (optional): MCP 제공자 (chatgpt, claude, cursor). 기본값: chatgpt
    - `options` (optional): 실행 옵션 (mode, temperature 등)

    ### Response:
    - `sessionId`: 생성된 세션 ID
    - `runId`: 생성된 실행 ID
    - `status`: 실행 상태
    - `preview`: 미리보기 메시지

    예시 요청:
    ```json
    {
      "providerId": "claude",
      "options": { "mode": "impl", "temperature": 0.2 }
    }
    ```

    예시 응답:
    ```json
    {
      "sessionId": "ss_0007",
      "runId": "run_0123",
      "status": "running",
      "preview": "지금부터 Task #3: 로그인 페이지 구현 작업을 시작합니다...",
      "summary": null
    }
    ```
    """
    return start_development_service(task_id, request, db)
