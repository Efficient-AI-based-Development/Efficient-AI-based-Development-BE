import asyncio

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from sse_starlette import EventSourceResponse
from starlette.requests import Request

from app.db.database import get_db
from app.db.models import ChatMessage, ChatSession
from app.domain.chat import (
    CANCEL_SENTINEL,
    END_SENTINEL,
    SESSION_CANCEL,
    SESSION_IN,
    SESSION_OUT,
    SESSION_TASK,
    apply_ai_last_message_to_content_service,
    create_chat_session_with_message_service,
    ensure_worker,
)
from app.schemas.chat import (
    ChatMessageRequest,
    ChatSessionCreateRequest,
    ChatSessionCreateResponse,
    StoreFileResponse,
)

router = APIRouter(prefix="/chats", tags=["chats"])


# chat 시작 & init_project 생성
@router.post("", response_model=ChatSessionCreateResponse, status_code=201)
async def start_chat_with_init_file(
    request: ChatSessionCreateRequest,
    user_id: str = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db),
):

    resp = create_chat_session_with_message_service(user_id, request.content_md, request, db)

    await ensure_worker(user_id, resp.chat_id, db)  # ① 워커 보장
    await SESSION_IN[resp.chat_id].put(request.content_md)

    return resp


@router.post("/{chat_session_id}/messages")
async def send_message(
    chat_session_id: int,
    request: ChatMessageRequest,
    user_id: str = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db),
):

    sess = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user_id, ChatSession.id == chat_session_id)
        .one_or_none()
    )
    if not sess:
        raise HTTPException(404, "chat session not found")

    if chat_session_id not in SESSION_OUT:
        # 스트림이 열리기 전 메시지 -> 무시할지, 저장만 할지 선택
        return {"ok": True, "ignored": True}

    db.add(
        ChatMessage(
            session_id=chat_session_id,
            role="user",
            content=request.content_md,
            user_id=user_id,
        )
    )
    db.commit()

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
    cancel_ev = SESSION_CANCEL.setdefault(chat_session_id, asyncio.Event())

    timeout = 300

    async def event_gen():
        try:
            while True:
                if await request.is_disconnected():
                    cancel_ev.set()
                    in_q = SESSION_IN.get(chat_session_id)
                    if in_q:
                        await in_q.put(CANCEL_SENTINEL)
                    break

                try:
                    token = await asyncio.wait_for(out_q.get(), timeout=timeout)
                except TimeoutError:
                    yield {"event": "timeout", "data": "no tokens, stream closed"}
                    cancel_ev.set()
                    in_q = SESSION_IN.get(chat_session_id)
                    if in_q:
                        await in_q.put(CANCEL_SENTINEL)
                    break

                if token == CANCEL_SENTINEL:
                    yield {"event": "cancel", "data": ""}
                    break

                if token == END_SENTINEL:
                    yield {"event": "turn_end", "data": ""}
                    break

                yield {"event": "assistant", "data": token}

        finally:
            pass

    return EventSourceResponse(event_gen(), ping=15000)


@router.post("/{chat_session_id}/cancel", status_code=202)
async def cancel_session(
    chat_session_id: int,
    user_id: str = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db),
):
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == chat_session_id, ChatSession.user_id == user_id)
        .first()
    )

    if session is None:
        # 네 스타일 기준 -> 404 사용
        raise HTTPException(404, "chat session not found or no permission")
    cancel_ev = SESSION_CANCEL.setdefault(chat_session_id, asyncio.Event())

    # 이미 취소 상태면 재진입 방지
    if cancel_ev.is_set():
        return {"ok": True}

    cancel_ev.set()

    # 워커 입력 쪽 취소 신호
    in_q = SESSION_IN.get(chat_session_id)
    if in_q:
        await in_q.put(CANCEL_SENTINEL)

    # 🔽 스트림 출력 쪽도 깨워서 즉시 종료되게
    out_q = SESSION_OUT.get(chat_session_id)
    if out_q:
        await out_q.put(CANCEL_SENTINEL)

    # 워커 태스크 취소
    task = SESSION_TASK.get(chat_session_id)
    if task and not task.done():
        task.cancel()

    return {"ok": True}


@router.post("/{chat_session_id}/store", response_model=StoreFileResponse, status_code=200)
def store_file(
    chat_session_id: int,
    user_id: str = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db),
):
    return apply_ai_last_message_to_content_service(user_id, chat_session_id, db)
