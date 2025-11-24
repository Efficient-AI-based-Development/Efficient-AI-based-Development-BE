import asyncio
import json
from contextlib import suppress
from dataclasses import dataclass, field
from typing import Any, TypeVar

from fastapi import Depends, HTTPException
from sqlalchemy.exc import IntegrityError, NoResultFound, SQLAlchemyError
from sqlalchemy.orm import Session
from sse_starlette import EventSourceResponse
from starlette.requests import Request

from app.api.v1.routes.ai import (
    generate_prd_endpoint,
    generate_srs_endpoint,
    generate_tasklist_endpoint,
    generate_userstory_endpoint,
    prd_chat,
    srs_chat,
    userstory_chat,
)
from app.db.database import get_db
from app.db.models import ChatMessage, ChatSession, Document, Project, Task, User
from app.domain.auth import get_current_user
from app.schemas.chat import (
    ChatMessageRequest,
    ChatSessionCreateRequest,
    ChatSessionCreateResponse,
    FileType,
    StoreFileResponse,
)

TIMEOUT = 300


@dataclass
class StateStation:
    session_id: int
    file_type: str | None = None

    queue_in: asyncio.Queue[str] = field(default_factory=asyncio.Queue)
    queue_out: asyncio.Queue[str] = field(default_factory=asyncio.Queue)
    task: asyncio.Task | None = None
    cancel_event: asyncio.Event = field(default_factory=asyncio.Event)
    last_msg: str | None = None
    last_doc: str | None = None


SESSIONS: dict[int, StateStation] = {}

# 전역 상수
END_SENTINEL = "[[END]]"
CANCEL_SENTINEL = "[[CANCEL]]"


async def start_chat_with_init_file_service(request: ChatSessionCreateRequest, current_user: User, db: Session):
    if isinstance(request.content_md, dict):
        request.content_md = json.dumps(request.content_md, ensure_ascii=False)

    resp = create_chat_session_with_message_service(current_user.user_id, request.content_md, request, db)

    await ensure_worker(current_user.user_id, resp.chat_id, request.file_type.value.upper(), db)  # ① 워커 보장
    attached_info = (
        db.query(ChatMessage).filter(ChatMessage.session_id == resp.chat_id, ChatMessage.role == "system").one_or_none()
    )
    content = ""

    if attached_info is None:
        content = request.content_md
    else:
        content = attached_info.content + request.content_md

    if request.file_type != FileType.project:
        await SESSIONS[resp.chat_id].queue_in.put(content)
    print(content)
    return resp


async def cancel_session_service(
    chat_session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.query(ChatSession).filter(ChatSession.id == chat_session_id, ChatSession.user_id == current_user.user_id).first()

    if session is None:
        # 네 스타일 기준 -> 404 사용
        raise HTTPException(404, "chat session not found or no permission")

    station = SESSIONS.get(chat_session_id)

    if station is None:
        station = StateStation(session_id=chat_session_id, file_type=session.file_type)
        SESSIONS[chat_session_id] = station

    cancel_ev = station.cancel_event
    # 이미 취소 상태면 재진입 방지
    if cancel_ev.is_set():
        return {"ok": True}
    cancel_ev.set()

    station = SESSIONS.get(chat_session_id)
    if station is None:
        station = StateStation(session_id=chat_session_id, file_type=session.file_type)
        SESSIONS[chat_session_id] = station
    # 워커 입력 쪽 취소 신호
    in_q = station.queue_in
    if in_q is not None:
        while True:
            try:
                in_q.get_nowait()  # 버리기
            except asyncio.QueueEmpty:
                break
        with suppress(asyncio.QueueFull):
            in_q.put_nowait(CANCEL_SENTINEL)

    station = SESSIONS.get(chat_session_id)
    if station is None:
        station = StateStation(session_id=chat_session_id, file_type=session.file_type)
        SESSIONS[chat_session_id] = station
    # 워커 입력 쪽 취소 신호
    out_q = station.queue_out
    if out_q is not None:
        while True:
            try:
                out_q.get_nowait()
            except asyncio.QueueEmpty:
                break
        with suppress(asyncio.QueueFull):
            out_q.put_nowait(CANCEL_SENTINEL)

    # 워커 태스크 취소
    station = SESSIONS.get(chat_session_id)
    if station is None:
        station = StateStation(session_id=chat_session_id, file_type=session.file_type)
        SESSIONS[chat_session_id] = station
    task = station.task
    if task and not task.done():
        task.cancel()
        # cancel 전파 기다리되, CancelledError는 조용히 무시
        with suppress(asyncio.CancelledError):
            await task

    station = SESSIONS.pop(chat_session_id, None)

    if station:
        # cancel 이벤 트리거
        station.cancel_event.set()

        # task가 살아있으면 cancel
        if station.task and not station.task.done():
            station.task.cancel()

    return {"ok": True}


async def send_message_service(
    chat_session_id: int,
    request: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sess = (
        db.query(ChatSession).filter(ChatSession.user_id == current_user.user_id, ChatSession.id == chat_session_id).one_or_none()
    )
    if not sess:
        raise HTTPException(404, "chat session not found")

    if chat_session_id not in SESSIONS:
        # 스트림이 열리기 전 메시지 -> 무시할지, 저장만 할지 선택
        return {"ok": True, "ignored": True}

    db.add(
        ChatMessage(
            session_id=chat_session_id,
            role="user",
            content=request.content_md,
            user_id=current_user.user_id,
        )
    )
    db.commit()
    # worker 보장
    await ensure_worker(current_user.user_id, chat_session_id, sess.file_type, db)

    # 큐에 user 메시지 삽입
    await SESSIONS[chat_session_id].queue_in.put(request.content_md)

    return {"ok": True}


async def stream_service(chat_session_id: int, request: Request, db: Session):
    sess = db.query(ChatSession).filter(ChatSession.id == chat_session_id).one_or_none()
    if not sess:
        raise HTTPException(404, "chat session not found")

    station = SESSIONS.get(chat_session_id)
    if not station:
        station = StateStation(session_id=chat_session_id, file_type=sess.file_type)
        SESSIONS[chat_session_id] = station
    out_q = station.queue_out
    cancel_ev = station.cancel_event

    async def event_gen():
        try:
            while True:
                if await request.is_disconnected():
                    cancel_ev.set()
                    station = SESSIONS.get(chat_session_id)
                    in_q = station.queue_in
                    if in_q is not None:
                        while True:
                            try:
                                in_q.get_nowait()  # 버리기
                            except asyncio.QueueEmpty:
                                break
                        with suppress(asyncio.QueueFull):
                            in_q.put_nowait(CANCEL_SENTINEL)

                    break

                try:
                    token = await asyncio.wait_for(out_q.get(), timeout=TIMEOUT)
                except TimeoutError:
                    yield {"event": "timeout", "data": "no tokens, stream closed"}
                    cancel_ev.set()
                    station = SESSIONS.get(chat_session_id)
                    in_q = station.queue_in
                    if in_q is not None:
                        while not in_q.empty():
                            try:
                                in_q.get_nowait()
                            except asyncio.QueueEmpty:
                                break
                        with suppress(asyncio.QueueFull):
                            in_q.put_nowait(CANCEL_SENTINEL)

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


# ---------------------- AI 작동 --------------------------------
async def ensure_worker(user_id: str, session_id: int, file_type: str, db: Session):
    # 1) 세션 스테이션 가져오기 또는 생성
    station = SESSIONS.get(session_id)
    if station is None:
        station = StateStation(session_id=session_id, file_type=file_type)
        SESSIONS[session_id] = station
    else:
        # 이미 있으면 file_type 업데이트만 (필요하면)
        station.file_type = file_type or station.file_type

    # 2) worker task 살아있으면 재사용
    if station.task and not station.task.done():
        return

    # 3) 취소 이벤트 초기화
    station.cancel_event.clear()

    doc = None
    task_content_md = None
    has_first = True
    msg = None
    data = None

    def build_prompt(session_id: int, new_message: str, db: Session) -> str:

        history = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.id.asc()).all()
        buf: list[str] = []
        buf.append("=== SYSTEM CONTEXT ===\n")

        system_content = history[0].content if history else ""
        buf.append(f"system : {system_content}\n\n")

        buf.append("=== CONVERSATION ===\n")
        for h in history[1:]:
            if h.role == "assistant":
                buf.append(f"AI: {h.content}\n")
            else:
                buf.append(f"USER: {h.content}\n")

        buf.append("\n=== NEW USER INPUT ===\n")
        buf.append(new_message)

        return "".join(buf)

    async def worker():
        nonlocal doc, task_content_md, has_first, msg, data
        try:
            while True:
                # 외부에서 취소되었으면 종료
                if station.cancel_event.is_set():
                    break

                # 새 유저 메시지 대기
                user_message = await station.queue_in.get()

                # 내부 프로토콜: [[CANCEL]] 이면 종료
                if user_message == CANCEL_SENTINEL:
                    break

                # 빈 문자열이면 바로 END 토큰만 쏘고 다음 루프
                if not isinstance(user_message, str) or not user_message.strip():
                    await station.queue_out.put(END_SENTINEL)
                    continue

                # 프롬프트 구성
                prompt = build_prompt(session_id, user_message, db)
                file_type_local = station.file_type
                if has_first:
                    if file_type_local == "PRD":
                        answer = generate_prd_endpoint(prompt)
                        data = answer.model_dump()
                        doc = data.get("prd_document")
                        msg = data.get("message")
                    elif file_type_local == "USER_STORY":
                        answer = generate_userstory_endpoint(prompt)
                        data = answer.model_dump()
                        doc = data.get("user_story")
                        msg = data.get("message")

                    elif file_type_local == "SRS":
                        answer = generate_srs_endpoint(prompt)
                        data = answer.model_dump()
                        doc = data.get("srs_document")
                        msg = data.get("message")

                    elif file_type_local == "TASK":
                        answer = generate_tasklist_endpoint("필요한 상위 문서의 내용은 user의 prompt에 넣었습니다", prompt)
                        data = answer.model_dump()
                        doc = data.get("tasks")
                        msg = data.get("message")

                    has_first = False
                else:
                    if file_type_local == "PRD":
                        answer = prd_chat(doc, prompt)
                        data = answer.model_dump()
                        doc = data.get("prd_document")
                        msg = data.get("message")
                    elif file_type_local == "USER_STORY":
                        answer = userstory_chat(doc, prompt)
                        data = answer.model_dump()
                        doc = data.get("user_story")
                        msg = data.get("message")

                    elif file_type_local == "SRS":
                        answer = srs_chat(doc, prompt)
                        data = answer.model_dump()
                        doc = data.get("srs_document")
                        msg = data.get("message")

                    elif file_type_local == "TASK":
                        answer = generate_tasklist_endpoint(task_content_md, prompt)
                        data = answer.model_dump()
                        doc = data.get("tasks")
                        msg = data.get("message")

                station.last_doc = doc

                await station.queue_out.put(
                    json.dumps(
                        {
                            "type": "data",
                            "doc": doc,
                            "message": msg,
                        },
                        ensure_ascii=False,  # 한글 깨지지 않게
                    )
                )

                if station.cancel_event.is_set():
                    break

                db.add(
                    ChatMessage(
                        session_id=session_id,
                        role="assistant",
                        content=msg,
                        user_id=user_id,
                    )
                )
                _safe_commit(db)

        except asyncio.CancelledError:
            # task.cancel() 된 경우 조용히 종료
            pass
        finally:
            # 정리: task 비우고 cancel_event 초기화
            station.cancel_event.clear()
            station.task = None

    # 4) 실제 worker task 실행
    station.task = asyncio.create_task(worker())


# ---------------------- 공통 유틸 ----------------------
def _http_400(msg: str) -> HTTPException:
    return HTTPException(status_code=400, detail=msg)


def _http_403(msg: str) -> HTTPException:
    return HTTPException(status_code=403, detail=msg)


def _http_404(msg: str) -> HTTPException:
    return HTTPException(status_code=404, detail=msg)


def _safe_commit(db: Session) -> None:
    """Commit 실패 시 롤백하고 HTTP 500으로 변환."""
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        # 무결성 위반(중복, FK 등)
        raise HTTPException(
            status_code=409,
            detail=f"Integrity error: {str(e.orig) if hasattr(e, 'orig') else str(e)}",
        )
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


T = TypeVar("T")


def _flush_and_refresh(db: Session, obj: T) -> T:
    """flush/refresh 래퍼(에러 → 500)."""
    try:
        db.flush()
        db.refresh(obj)
        return obj
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database flush error: {str(e)}")


def _ensure_enum(ft: FileType | str) -> FileType:
    """문자/enum 혼용 대비."""
    if isinstance(ft, FileType):
        return ft
    try:
        return FileType(ft)
    except Exception:
        raise _http_400(f"Invalid file_type: {ft}")


######################################### SERVICE #############################################
def apply_ai_last_message_to_content_service(user_id: str, chat_session_id: int, project_id: int, db: Session):
    cur_chat_session = (
        db.query(ChatSession).filter(ChatSession.id == chat_session_id, ChatSession.user_id == user_id).one_or_none()
    )
    if cur_chat_session is None:
        raise HTTPException(404, "Chat session not found")
    station = SESSIONS.get(chat_session_id)
    if station is None:
        raise HTTPException(404, "Chat session not found")

    if station.last_doc is None:
        raise _http_404("No create File for this session.")
    updated_obj = store_document_content(user_id, cur_chat_session, project_id, station.last_doc, db)
    db.commit()

    if updated_obj is None:  # Task 같은 경우에는 새로 생성되기 때문에 X
        updated_at = None

    else:
        try:
            db.refresh(updated_obj)
            updated_at = getattr(updated_obj, "updated_at", None)
        except Exception:
            updated_at = None

    return StoreFileResponse(
        ok=True,
        file_type=cur_chat_session.file_type,
        file_id=cur_chat_session.file_id,
        updated_at=updated_at,
    )


def update_doc_file_service(user_id: str, project_id: int, db: Session):
    proj = db.query(Project).filter(Project.id == project_id, Project.owner_id == user_id).one_or_none()
    if proj is None:
        raise HTTPException(404, "Project not found")

    doc_names = {
        "PRD": "Product Requirements Document",
        "USER_STORY": "User Story Document",
        "SRS": "Software Requirement Specification Document",
    }

    for doc_type in ["SRS", "USER_STORY", "PRD"]:

        prompt = (
            "전체 TASK 목록이 갱신되었습니다.\n"
            f"현재 생성해야 하는 문서는 **{doc_names[doc_type]} ({doc_type})** 입니다.\n"
            "기존 및 변경된 TASK 내용을 모두 반영하여 최신 버전으로 다시 작성하세요."
        )
        doc = ""
        attached_info = insert_file_info(user_id, project_id, db)
        if doc_type == "PRD":
            doc = prd_chat(attached_info, prompt).model_dump()["prd_document"]
        elif doc_type == "USER_STORY":
            doc = userstory_chat(attached_info, prompt).model_dump()["user_story"]
        elif doc_type == "SRS":
            doc = srs_chat(attached_info, prompt).model_dump()["srs_document"]

        data = (
            db.query(Document)
            .filter(Document.author_id == user_id, Document.project_id == project_id, Document.type == doc_type)
            .one_or_none()
        )
        if data:
            data.content_md = doc or data.content_md
        db.commit()
        db.refresh(data)


def store_document_content(
    user_id: str,
    cur_chat_session: ChatSession,
    project_id: int,
    content_md: str | None,
    db: Session,
):
    content_md = content_md if content_md else ""
    file_type = cur_chat_session.file_type
    file_id = cur_chat_session.file_id
    if file_type == "PROJECT":
        proj = db.query(Project).filter(Project.owner_id == user_id, Project.id == file_id).one()

        try:
            parsed = json.loads(content_md)
            proj.content_md = parsed.get("project_document")
        except Exception:
            proj.content_md = content_md  # 그냥 raw text 저장

        db.add(proj)
        return proj

    elif file_type in ("PRD", "USER_STORY", "SRS"):
        doc = db.query(Document).filter(Document.author_id == user_id, Document.id == file_id, Document.type == file_type).one()

        try:
            if cur_chat_session.file_type == "PRD":
                doc.content_md = content_md
            elif cur_chat_session.file_type == "USER_STORY":
                doc.content_md = content_md
            elif cur_chat_session.file_type == "SRS":
                doc.content_md = content_md
        except Exception:
            doc.content_md = content_md

        doc.content_md = content_md
        db.add(doc)
        return doc

    elif file_type == "TASK":
        tasks = db.query(Task).filter(Task.project_id == project_id).first()
        for task in content_md:
            data = Task(
                project_id=project_id,
                title=task["title"],
                tags=task["tag"],
                priority=task["priority"],
                description=task["description"],
                description_md=task["description"],
            )
            db.add(data)
        # task 생성
        if tasks is None:
            return None

        # task 추가 생성
        else:
            return 1

    else:
        raise _http_400(f"Unsupported file_type: {file_type}")


def create_chat_session_with_message_service(
    user_id: str,
    user_message: str,
    request: ChatSessionCreateRequest,
    db: Session,
):
    # 입력 검증
    if not user_id:
        raise _http_400("X-User-ID header required.")
    if request is None:
        raise _http_400("Request body is required.")

    # 파일 존재 O -> 불러오기, 파일 존재 X -> 파일 생성 후 불러오기
    # Task일 경우 없을때 생성 X -> file = None, file_type = "Task"
    file, file_type = create_and_check_file_id(user_id, request, db)

    # chat session 생성
    chat_session = create_chat_session(user_id, file, file_type, db)

    # file(생성) 상위 file content를 chat message에 미리 등록,
    # cf) Project -> 입력X, userstory -> project, prd 내용 등록

    # file(수정) 자신을 포함한 상위 file content를 chat message에 미리 등록,
    # cf) Project -> Project, userstory -> project, prd, userstory 내용 등록
    result = attached_info_to_chat(user_id, chat_session.id, request, file, file_type, db)

    # 사용자 입력 메시지 저장
    content = ""
    # 기존 task존재, task 추가하는 경우
    if result == 0:
        content = user_message

    else:
        content = (
            "description을 작성할때 Markdown형식으로 구체적으로 작성해야합니다.\n"
            "======== 예시 ========="
            "## 요구사항\n"
            "- 키워드 검색 및 카테고리, 가격, 상태, 위치 필터 적용\n"
            "- 입력 시 디바운스 검색 기능\n"
            "- 검색 결과 페이징 처리\n"
            "## 구현 세부사항\n"
            "- REST API(`GET /api/items?search=...&category=...`) 호출로 서버 측 필터링\n"
            "- lodash.debounce로 디바운스 처리\n"
            "- 결과 정렬 및 페이징은 React Query 또는 SWR로 구현\n"
            "## 테스트 전략\n"
            "- 검색어 및 필터 조합별로 API 호출 파라미터 검증 단위 테스트\n"
            "- 통합 테스트로 다양한 필터 조합 결과 확인\n"
            "========== 예시 종료 ===========\n\n"
        )
        if result == 1:
            content = (
                user_message
                + content
                + (
                    "PRD, USER_STORY, SRS, TASK 문서를 토대로 user_input에 따라 추가적인 TASK를 생성하려고 합니다."
                    "이때 기존의 TASK는 출력하지 않고 추가로 작성된 TASK만 출력해주세요."
                    "출력되는 TASK들의 제목도 작성해야합니다"
                )
            )

    db.add(ChatMessage(session_id=chat_session.id, role="user", content=content, user_id=user_id))
    db.commit()

    # 파일 프로젝트 새로 생성하는 경우 때문에 작성
    # project = -1일 경우 request.project_id 바로 사용 불가
    # 존재하지 않는 Task인 경우
    if file is None:
        project_id = request.project_id
    else:
        project_id = file.id if isinstance(file, Project) else file.project_id

    return ChatSessionCreateResponse(
        chat_id=chat_session.id,
        stream_url=f"/api/v1/chats/{chat_session.id}/stream",
        file_type=request.file_type,
        project_id=project_id,
        created_at=chat_session.created_at,
    )


######################################### REPO #############################################


def attached_info_to_chat(
    user_id: str,
    chat_session_id: int,
    request: ChatSessionCreateRequest,
    file: Any,
    file_type: str,
    db: Session,
) -> int:
    # 문서 내용 작성
    result = insert_file_info_repo(user_id, chat_session_id, request, file, file_type, db)
    db.commit()
    return result


def create_chat_message(user_id: str, chat_session_id: int, role: str, content: str, db: Session) -> ChatMessage:
    chat_message = ChatMessage(user_id=user_id, session_id=chat_session_id, role=role, content=content)
    chat_message = create_chat_message_repo(chat_message, db)
    db.commit()
    return chat_message


def create_and_check_file_id(user_id: str, request: ChatSessionCreateRequest, db: Session) -> tuple[Any, str]:
    # project_id = -1 인 경우 -> 프로젝트 생성
    if request.project_id == -1:
        if request.file_type is FileType.project:
            file, file_type = create_file_repo(user_id, request, db)

            # PRD 생성
            request.project_id = file.id
            request.file_type = FileType.prd
            file1, file_type1 = create_file_repo(user_id, request, db)

            # USER_STORY 생성
            request.file_type = FileType.userstory
            file2, file_type2 = create_file_repo(user_id, request, db)

            # SRS 생성
            request.file_type = FileType.srs
            file3, file_type3 = create_file_repo(user_id, request, db)

            request.file_type = FileType.project

        else:
            raise _http_400(
                "project_id = -1 은 PROJECT 생성에만 사용할 수 있습니다. " "문서/태스크는 기존 project_id가 필요합니다."
            )
    else:  # 파일 존재 확인

        # Step 1. 프로젝트 존재 여부 + 권한 체크
        project = db.query(Project).filter(Project.id == request.project_id, Project.owner_id == user_id).one_or_none()
        if project is None:
            # 여기서 프로젝트 없으면 세션 생성 금지
            raise _http_404(f"Project(id={request.project_id}) not found or no permission.")

        file, file_type = check_file_exist_repo(user_id, request, db)
        # file None이면 존재하지 않는 파일 (PRD/USER_STORY/SRS/TASK) -> 파일 생성
        if file is None:
            if request.file_type in (FileType.prd, FileType.userstory, FileType.srs):
                file, file_type = create_file_repo(user_id, request, db)
            elif request.file_type is FileType.task:  # task 는 ai마지막에 생성
                return None, file_type
            elif request.file_type is FileType.project:
                raise _http_404(f"Project(id={request.project_id}) not found or no permission.")
            else:
                raise _http_400(f"Unsupported file_type: {request.file_type}")

    db.commit()
    return file, file_type


def create_chat_session(user_id: str, file: Any, file_type: str, db: Session) -> ChatSession:
    if isinstance(file, (Project | Document)):
        target_file_id = file.id
    elif isinstance(file, Task):  # TASK 존재 하는 경우
        target_file_id = file.id

    else:
        # TASK가 존재 하지 않아 임의 id 부여
        if file_type == "TASK":
            last = db.query(Task).order_by(Task.id.desc()).first()
            target_file_id = (last.id if last else 0) + 1
        else:
            raise _http_400(f"Unsupported file type for session: {type(file)}")

    chat_session = ChatSession(
        user_id=user_id,
        file_type=file_type,
        file_id=target_file_id,
    )
    store_chat_session_repo(chat_session, db)
    db.commit()
    return chat_session


######################################### REPO #############################################
def insert_file_info(user_id: str, project_id: int, db: Session) -> str:
    parts = []

    def _get_doc(t: str) -> str | None:
        d = db.query(Document).filter_by(author_id=user_id, project_id=proj_id, type=t).one_or_none()
        return d.content_md if d else None

    proj = db.query(Project).filter(Project.owner_id == user_id, Project.id == project_id).one_or_none()
    if not proj:
        raise _http_404(f"Project {project_id} not found or no permission.")
    proj_id = proj.id
    parts.append(f"PROJECT:\n{proj.content_md or ''}")
    for t in ["PRD", "USER_STORY", "SRS"]:
        content = _get_doc(t)
        if content:
            parts.append(f"{t}:\n{content}\n")
    task = db.query(Task).filter(Task.project_id == project_id).order_by(Task.id.asc()).all()
    if task:
        for i, t in enumerate(task, start=1):
            content_md = t.description_md or ""
            parts.append(f"TASK {i}번:\n{content_md}\n")

    content = "\n\n---\n".join([p for p in parts if p])
    return content


def insert_file_info_repo(
    user_id: str,
    chat_session_id: int,
    request: ChatSessionCreateRequest,
    file: Any,
    file_type: str,
    db: Session,
):
    parts: list[str] = []

    def _get_doc(t: str) -> str | None:
        d = db.query(Document).filter_by(author_id=user_id, project_id=proj_id, type=t).one_or_none()
        return d.content_md if d else None

    if isinstance(file, Project):
        proj = db.query(Project).filter(Project.owner_id == user_id, Project.id == file.id).one_or_none()
        if not proj:
            raise _http_404(f"Project {file.id} not found or no permission.")
        proj_id = proj.id
        parts.append(f"PROJECT:\n{proj.content_md or ''}")

    elif isinstance(file, (Document | Task)):
        proj = db.query(Project).filter(Project.owner_id == user_id, Project.id == file.project_id).one_or_none()
        if not proj:
            raise _http_404(f"Project {file.project_id} not found or no permission.")
        proj_id = proj.id
        parts.append(f"PROJECT:\n{proj.content_md or ''}")
        for t in ["PRD", "USER_STORY", "SRS"]:
            content = _get_doc(t)
            if content:
                parts.append(f"{t}:\n{content}\n")
        task = db.query(Task).filter(Task.project_id == file.project_id).order_by(Task.id.asc()).all()
        if task:
            for i, t in enumerate(task, start=1):
                content_md = t.description_md or ""
                parts.append(f"TASK {i}번:\n{content_md}\n")

    # Task 파일 존재하지 않는 경우
    elif file_type == "TASK":
        proj = db.query(Project).filter(Project.owner_id == user_id, Project.id == request.project_id).one_or_none()
        if not proj:
            raise _http_404(f"Project {request.project_id} not found or no permission.")
        proj_id = proj.id
        parts.append(f"PROJECT:\n{proj.content_md or ''}")
        for t in ["PRD", "USER_STORY", "SRS"]:
            content = _get_doc(t)
            if content:
                parts.append(f"{t}:\n{content}\n")

    content = "\n\n---\n".join([p for p in parts if p])
    if content:
        db.add(
            ChatMessage(
                session_id=chat_session_id,
                role="system",
                user_id=user_id,
                content=content,
            )
        )
    # TASK 파일 추가를 원하는 경우, user_input에 요구사항 추가를 위해 구분
    if isinstance(file, Task):
        return 1
    # 새로 생성하는 TASK인 경우
    elif file_type == "TASK":
        return 2
    else:
        return 0


def create_chat_message_repo(chat_message: ChatMessage, db: Session) -> ChatMessage:
    try:
        db.add(chat_message)
        return _flush_and_refresh(db, chat_message)
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Failed to create chat message: {str(e)}")


def check_file_exist_repo(user_id: str, request: ChatSessionCreateRequest, db: Session) -> tuple[Any, str] | tuple[None, str]:
    # request body의 project id와 file_type 조합으로 유무 판별
    # type = project인 경우 project 수정임
    if request.file_type is FileType.project:
        try:
            proj = db.query(Project).filter(Project.owner_id == user_id, Project.id == request.project_id).one()
            return proj, "PROJECT"
        except NoResultFound:
            return None, "PROJECT"

    # type = (나머지) - db 조회를 통해서 생성/수정 알아내야함
    else:
        if request.file_type in (FileType.prd, FileType.userstory, FileType.srs):
            doc_type = request.file_type.value.upper()
            doc: Document | None = (
                db.query(Document)
                .filter(
                    Document.author_id == user_id,
                    Document.project_id == request.project_id,
                    Document.type == doc_type,
                )
                .one_or_none()
            )
            return doc, doc_type

        elif request.file_type is FileType.task:  # task일 경우
            temp_type = request.file_type.value.upper()
            file = db.query(Task).filter(Task.project_id == request.project_id).first()
            return file, temp_type

        else:
            raise _http_400(f"Unsupported file_type: {request.file_type}")


def create_file_repo(user_id: str, request: ChatSessionCreateRequest, db: Session) -> tuple[Any, str]:

    if request.file_type is FileType.project:
        data = json.loads(request.content_md)
        title = data.get("title", "New Project")
        file = Project(
            title=title,
            owner_id=user_id,
            content_md=request.content_md,
            status="in_progress",
        )
        try:
            db.add(file)
            _flush_and_refresh(db, file)
            return file, "PROJECT"
        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to create project: {str(e)}")

    elif request.file_type in (FileType.prd, FileType.userstory, FileType.srs):
        if request.project_id in (-1, None):
            raise _http_400("문서 생성에는 유효한 project_id가 필요합니다.")
        doc_type = request.file_type.value.upper()
        # 소유 프로젝트인지 확인
        proj = db.query(Project).filter(Project.owner_id == user_id, Project.id == request.project_id).one_or_none()
        if proj is None:
            raise _http_404(f"Project(id={request.project_id}) not found or no permission.")

        file = Document(
            project_id=request.project_id,
            title=f"New {doc_type} Document",
            author_id=user_id,
            type=doc_type,
        )
        try:
            db.add(file)
            _flush_and_refresh(db, file)
            return file, doc_type
        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to create document: {str(e)}")

    elif request.file_type is FileType.task:
        raise _http_400("Task auto-creation is not supported here. Use Task API.")

    else:
        raise _http_400(f"Unsupported file_type: {request.file_type}")


def store_chat_session_repo(chat: ChatSession, db: Session) -> ChatSession:
    try:
        db.add(chat)
        return _flush_and_refresh(db, chat)
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Failed to create chat session: {str(e)}")
