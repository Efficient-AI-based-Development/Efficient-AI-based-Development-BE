from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.db.database import get_db
from app.db.models import User
from app.domain.auth import get_current_user
from app.domain.chat import (
    apply_ai_last_message_to_content_service,
    cancel_session_service,
    send_message_service,
    start_chat_with_init_file_service,
    stream_service,
)
from app.schemas.chat import (
    ChatMessageRequest,
    ChatSessionCreateRequest,
    ChatSessionCreateResponse,
    StoreFileRequest,
    StoreFileResponse,
)

router = APIRouter(prefix="/chats", tags=["chats"], dependencies=[Depends(get_current_user)])


# chat 시작 & init_project 생성
@router.post("", response_model=ChatSessionCreateResponse, status_code=201)
async def start_chat_with_init_file(
    request: ChatSessionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await start_chat_with_init_file_service(request, current_user, db)


# SSE 연결, AI 응답 보내기
@router.get("/{chat_session_id}/stream")
async def stream(chat_session_id: int, request: Request, db: Session = Depends(get_db)):
    return await stream_service(chat_session_id, request, db)


@router.post("/{chat_session_id}/messages")
async def send_message(
    chat_session_id: int,
    request: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await send_message_service(chat_session_id, request, current_user, db)


@router.post("/{chat_session_id}/cancel", status_code=202)
async def cancel_session(
    chat_session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return cancel_session_service(chat_session_id, current_user, db)


@router.post("/{chat_session_id}/store", response_model=StoreFileResponse, status_code=200)
def store_file(
    chat_session_id: int,
    request: StoreFileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return apply_ai_last_message_to_content_service(current_user.user_id, chat_session_id, request.project_id, db)
