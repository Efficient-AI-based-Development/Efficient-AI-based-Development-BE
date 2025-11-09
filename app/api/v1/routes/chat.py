import time
from typing import Iterator

from fastapi import APIRouter, Depends, Header, Path, HTTPException
from sqlalchemy.orm import Session
from sse_starlette import EventSourceResponse

from app.db.database import get_db
from app.db.models import ChatSession, ChatMessage
from app.domain.chat import create_chat_session_with_message_service, fake_sync_llm
from app.schemas.chat import ChatSessionCreateRequest, ChatSessionCreateResponse, ChatMessageRequest

router = APIRouter(prefix="/chats", tags=["chats"])

# chat 시작 & init_project 생성
@router.post("", response_model=ChatSessionCreateResponse, status_code=201)
def start_chat_with_init_file(user_id: Header(..., alias="X-User-ID"), request: ChatSessionCreateRequest, db: Session = Depends(get_db)):
    return create_chat_session_with_message_service(user_id, request, db)

@router.post("/{chat_session_id}/messages")
def save_user_message(
    chat_session_id: int,
    request: ChatMessageRequest,
    user_id : str = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db),
):
    sess = db.query(ChatSession).filter(ChatSession.id == chat_session_id).one_or_none()
    if not sess:
        raise HTTPException(404, "chat session not found")

    msg = ChatMessage(
        session_id=sess.id,
        role="user",
        user_id=user_id,
        content=request.content_md,
    )
    db.add(msg)
    db.refresh(msg)
    db.commit()
    return msg

# SSE 연결, AI 응답 보내기
@router.get("/{chat_session_id}/stream")
def stream_sse(
    chat_session_id: int = Path(...),
    db: Session = Depends(get_db),
):
    sess = db.query(ChatSession).filter(ChatSession.id == chat_session_id).one_or_none()
    if not sess:
        raise HTTPException(404, "chat session not found")

    # 가장 최근 user 메시지 하나를 가져와 응답 생성(데모)
    last_user = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == sess.id, ChatMessage.role == "user")
        .order_by(ChatMessage.id.desc())
        .first()
    )
    prompt = last_user.content if last_user else "(empty)"

    # 4) EventSourceResponse 반환
    #    - ping으로 keep-alive(프록시 타임아웃 방지)
    #    - media_type은 text/event-stream 고정
    #    - 동기 제너레이터도 동작함
    resp = EventSourceResponse(
        gen,
        ping=15,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )

    # 최종 전체 본문 저장(옵션)
    full_text = " ".join([
        "안녕하세요!", "동기 SSE 데모 응답입니다.", f"(요약:{prompt[:60]})"
    ])
    # 응답을 DB에 저장
    db.add(ChatMessage(session_id=sess.id, role="assistant", content=full_text))
    db.commit()

    return EventSourceResponse(fake_sync_llm(prompt))




# # 프로젝트 기초 세팅
# @router.post("", response_model=ChatSessionCreateResponse, status_code=201)
# def create_chat_session_update_project(user_id: str, project):
#     # 프로젝트 기초 세팅 값 받아서 파일 수정
#     update_init_project(user_id, request)
#
#     # chat messasge DB 저장
#     store_chat_message(chat_id, request)
#
#     # chat -> AI보내기
#
#     # return 성공/실패
#
# # 채팅 보내기
# @router.post(~)
# def receive_user_message(chat_id, project):
#     # 채팅 저장하기
#
#     # AI로 보내기
#

#
# # 채팅 종료, AI 출력 내용 문서화
# @router.GET(~)
# def chat_close_documentation()
