import asyncio

from fastapi import APIRouter, Header, Depends, HTTPException
from sqlalchemy.orm import Session
from sse_starlette import EventSourceResponse
from starlette.requests import Request

from app.db.database import get_db
from app.db.models import ChatSession
from app.domain.chat import create_chat_session_with_message_service, ensure_worker, SESSION_IN, SESSION_OUT, \
    SESSION_TASK
from app.schemas.chat import ChatSessionCreateResponse, ChatSessionCreateRequest, ChatMessageRequest

router = APIRouter(prefix="/chats", tags=["chats"])

# 세션별 in/out 큐 + 워커 태스크


# chat 시작 & init_project 생성
@router.post("", response_model=ChatSessionCreateResponse, status_code=201)
async def start_chat_with_init_file(request: ChatSessionCreateRequest, user_id: str = Header(..., alias="X-User-ID"),  db: Session = Depends(get_db)):

    resp = create_chat_session_with_message_service(user_id, request, db)
    await ensure_worker(user_id, resp.chat_id, db)                                  # ① 워커 보장
    await SESSION_IN[resp.chat_id].put(request.content_md)

    return resp

@router.post("/{chat_session_id}/messages")
async def send_message(
    chat_session_id: int,
    request: ChatMessageRequest,
    user_id: str = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db),
):

    sess = db.query(ChatSession).filter(ChatSession.user_id == user_id, ChatSession.id == chat_session_id).one_or_none()
    if not sess:
        raise HTTPException(404, "chat session not found")

    # worker 보장
    await ensure_worker(user_id, chat_session_id, db)

    # 큐에 user 메시지 삽입
    await SESSION_IN[chat_session_id].put(request.content_md)

    return {"ok": True}


# SSE 연결, AI 응답 보내기
@router.get("/{chat_session_id}/stream")
async def stream(chat_session_id: int, request: Request, db: Session = Depends(get_db)):

    sess = db.query(ChatSession).filter(ChatSession.id == chat_session_id).one_or_none()
    if not sess:
        raise HTTPException(404, "chat session not found")

    out_q = SESSION_OUT.setdefault(chat_session_id, asyncio.Queue())

    TIMEOUT = 300

    async def event_gen():
        try:
            while True:

                if await request.is_disconnected():
                    print("client closed")
                    break

                try:
                    token = await asyncio.wait_for(out_q.get(), timeout=TIMEOUT)
                except asyncio.TimeoutError:
                    yield {"event": "timeout", "data": "no tokens, stream closed"}
                    break

                # 3) 토큰에 따른 출력
                if token == "[[END]]":
                    yield {"event": "turn_end", "data": ""}
                    continue
                else:
                    yield {"event": "delta", "data": token}

        except asyncio.CancelledError:
            pass

        finally:
            task = SESSION_TASK.get(chat_session_id)
            if task:
                task.cancel()
            print(f"stream closed for session {chat_session_id}")

    return EventSourceResponse(event_gen(), ping=15000)






