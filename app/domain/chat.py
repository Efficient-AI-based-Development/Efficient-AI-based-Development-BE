import asyncio
from typing import Any

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError, NoResultFound, SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models import ChatMessage, ChatSession, Document, Project, Task
from app.schemas.chat import (
    ChatSessionCreateRequest,
    ChatSessionCreateResponse,
    FileType,
    StoreFileResponse,
)

SESSION_IN: dict[int, asyncio.Queue[str]] = {}
SESSION_OUT: dict[int, asyncio.Queue[str]] = {}
SESSION_TASK: dict[int, asyncio.Task] = {}
SESSION_CANCEL: dict[int, asyncio.Event] = {}

STREAM_READY: dict[int, asyncio.Event] = {}


# 전역 상수
END_SENTINEL = "[[END]]"
CANCEL_SENTINEL = "[[CANCEL]]"


# ---------------------- AI 작동 --------------------------------
async def ensure_worker(user_id: str, session_id: int, db: Session):
    # 이미 실행 중이면 재사용
    task = SESSION_TASK.get(session_id)
    if task and not task.done():
        return

    in_q = SESSION_IN.setdefault(session_id, asyncio.Queue())
    out_q = SESSION_OUT.setdefault(session_id, asyncio.Queue())
    cancel_ev = SESSION_CANCEL.setdefault(session_id, asyncio.Event())

    def build_prompt(session_id: int, new_message: str, db: Session):

        history = db.query(ChatMessage) \
            .filter(ChatMessage.session_id == session_id) \
            .order_by(ChatMessage.id.asc()) \
            .all()

        buf = []
        buf.append("=== SYSTEM CONTEXT ===\n")

        buf.append("system : " + history[0].content)
        buf.append("\n")

        # HISTORY
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
        try:
            while True:
                # 외부에서 취소되었으면 종료
                if cancel_ev.is_set():
                    break

                user_message = await in_q.get()


                # 내부 프로토콜: [[CANCEL]] 메시지를 받으면 종료
                if user_message == "[[CANCEL]]":
                    break

                if not isinstance(user_message, str) or not user_message.strip():
                    await out_q.put("[[END]]")
                    continue

                prompt = build_prompt(session_id, user_message, db)

                # 여기서는 가짜 스트리밍
                assembled: list[str] = []
                for token in prompt:
                    if cancel_ev.is_set():    # 스트림 도중 취소되면 즉시 중단
                        break
                    await asyncio.sleep(0.05)
                    assembled.append(token)
                    await out_q.put(token)

                await out_q.put("[[END]]")   # 턴 종료 이벤트

                # 취소가 중간에 들어왔으면 저장 스킵
                if cancel_ev.is_set():
                    break

                # 어시스턴트 전체 응답 저장
                full_text = "".join(assembled)
                db.add(
                    ChatMessage(
                        session_id=session_id,
                        role="assistant",
                        content=full_text,
                        user_id=user_id,
                    )
                )
                _safe_commit(db)

        except asyncio.CancelledError:
            pass
        finally:
            # 정리
            cancel_ev.clear()
            SESSION_TASK.pop(session_id, None)

    SESSION_TASK[session_id] = asyncio.create_task(worker())



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
        raise HTTPException(status_code=409, detail=f"Integrity error: {str(e.orig) if hasattr(e, 'orig') else str(e)}")
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

def _flush_and_refresh(db: Session, obj: Any) -> Any:
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
def apply_ai_last_message_to_content_service(
    user_id: str, chat_session_id: int, db: Session
):
    cur_chat_session = (
        db.query(ChatSession)
        .filter(ChatSession.id == chat_session_id, ChatSession.user_id == user_id)
        .one_or_none()
    )
    if cur_chat_session is None:
        raise HTTPException(404, "Chat session not found")
    last_assistant_message = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == chat_session_id, ChatMessage.role == "assistant")
        .order_by(ChatMessage.id.desc())
        .first()
    )
    if not last_assistant_message:
        raise _http_404("No assistant message found for this session.")
    updated_obj = store_document_content(user_id, cur_chat_session, last_assistant_message.content, db)

    db.commit()
    try:
        db.refresh(updated_obj)  # updated_at 같은 DB 생성 값이 필요할 때
        updated_at = getattr(updated_obj, "updated_at", None)
    except Exception:
        updated_at = None

    return StoreFileResponse(
        ok=True,
        file_type=cur_chat_session.file_type,
        file_id=cur_chat_session.file_id,
        updated_at=updated_at
    )

def store_document_content(user_id: str, cur_chat_session: ChatSession, content_md: str, db: Session):
    file_type = cur_chat_session.file_type
    file_id = cur_chat_session.file_id
    if file_type == "PROJECT":
        proj = db.query(Project).filter(Project.owner_id == user_id, Project.id == file_id).one()
        proj.content_md = content_md
        db.add(proj)
        return proj

    elif file_type in ("PRD", "USER_STORY", "SRS"):
        doc = db.query(Document).filter(Document.author_id == user_id, Document.id == file_id, Document.type == file_type).one()
        doc.content_md = content_md
        db.add(doc)
        return doc

    elif file_type == "TASK":
        return None

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
    file, file_type = create_and_check_file_id(user_id, request, db)

    # chat session 생성
    chat_session = create_chat_session(user_id, file, file_type, db)



    # file(생성) 상위 file content를 chat message에 미리 등록
    # cf) Project -> 입력X, userstory -> project, prd 내용 등록
    # file(수정) 자신을 포함한 상위 file content를 chat message에 미리 등록
    # cf) Project -> Project, userstory -> project, prd, userstory 내용 등록
    attached_info_to_chat(user_id, chat_session.id, file, file_type, db)

    # 사용자 발화 저장
    db.add(
        ChatMessage(
            session_id=chat_session.id,
            role="user",
            content=user_message,
            user_id=user_id,
        )
    )

    return ChatSessionCreateResponse(
        chat_id=chat_session.id,
        stream_url=f"/api/v1/chats/{chat_session.id}/stream",
        file_type=request.file_type,
        project_id=file.id if isinstance(file, Project) else file.project_id,
        created_at=chat_session.created_at,
    )






######################################### REPO #############################################


def attached_info_to_chat(user_id: str, chat_session_id: int, file: Any, file_type: str, db: Session) -> None:
    # 문서 내용 작성
    # Project 작성 시
    insert_file_info_repo(user_id, chat_session_id, file, file_type, db)
    db.commit()


def create_chat_message(user_id: str, chat_session_id: int, role: str, content: str, db: Session) -> ChatMessage:
    chat_message = ChatMessage(
        user_id=user_id, session_id=chat_session_id, role=role, content=content
    )
    chat_message = create_chat_message_repo(chat_message, db)
    db.commit()
    return chat_message

def create_and_check_file_id(
    user_id: str, request: ChatSessionCreateRequest, db: Session
) -> tuple[Any, str]:
    # project_id = -1 인 경우 -> 프로젝트 생성
    if request.project_id == -1:
        if request.file_type is FileType.project:
            file, file_type = create_file_repo(user_id, request, db)
        else:
            raise _http_400(
                "project_id = -1 은 PROJECT 생성에만 사용할 수 있습니다. "
                "문서/태스크는 기존 project_id가 필요합니다."
            )
    else:  # 파일 존재 확인

        # Step 1. 프로젝트 존재 여부 + 권한 체크
        project = db.query(Project).filter(
            Project.id == request.project_id,
            Project.owner_id == user_id
        ).one_or_none()
        if project is None:
            # 여기서 프로젝트 없으면 세션 생성 금지
            raise _http_404(f"Project(id={request.project_id}) not found or no permission.")


        file, file_type = check_file_exist_repo(user_id, request, db)
        # file None이면 존재하지 않는 파일 (PRD/USER_STORY/SRS/TASK) -> 파일 생성
        if file is None:
            if request.file_type in (FileType.prd, FileType.userstory, FileType.srs):
                file, file_type = create_file_repo(user_id, request, db)
            elif request.file_type is FileType.task:
                raise _http_404(f"Task(id={request.project_id}) not found.")
            elif request.file_type is FileType.project:
                raise _http_404(f"Project(id={request.project_id}) not found or no permission.")
            else:
                raise _http_400(f"Unsupported file_type: {request.file_type}")

    db.commit()
    return file, file_type

def create_chat_session(
    user_id: str, file: Any, file_type: str, db: Session
) -> ChatSession:
    if isinstance(file, (Project, Document, Task)):
        target_file_id = file.id
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

def insert_file_info_repo(
    user_id: str, chat_session_id: int, file: Any, file_type: str, db: Session
):
    parts: list[str] = []

    def _get_doc(t: str) -> str | None:
        d = db.query(Document).filter_by(author_id=user_id, project_id=proj_id, type=t).one_or_none()
        return getattr(d, "content_md", None) if d else None

    if isinstance(file, Project):
        proj = db.query(Project).filter(Project.owner_id == user_id, Project.id == file.id).one_or_none()
        if not proj:
            raise _http_404(f"Project {file.id} not found or no permission.")
        proj_id = proj.id
        parts.append(proj.content_md or "")

    elif isinstance(file, Document):
        proj = db.query(Project).filter(Project.owner_id == user_id, Project.id == file.project_id).one_or_none()
        if not proj:
            raise _http_404(f"Project {file.project_id} not found or no permission.")
        proj_id = proj.id
        parts.append(proj.content_md or "")
        parts.append(_get_doc("PRD") or "")
        parts.append(_get_doc("USER_STORY") or "")
        parts.append(_get_doc("SRS") or "")

    elif isinstance(file, Task):
        return  # 필요 시 태스크 컨텍스트 추가

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




def create_chat_message_repo(chat_message: ChatMessage, db: Session) -> ChatMessage:
    try:
        db.add(chat_message)
        return _flush_and_refresh(db, chat_message)
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Failed to create chat message: {str(e)}")



def check_file_exist_repo(
    user_id: str, request: ChatSessionCreateRequest, db: Session
) -> tuple[Any, str] | tuple[None, str]:
    # request body의 project id와 file_type 조합으로 유무 판별

    # type = project인 경우 project 수정임
    if request.file_type is FileType.project:
        try:
            file = db.query(Project).filter(
                Project.owner_id == user_id,
                Project.id == request.project_id
            ).one()
            return file, "PROJECT"
        except NoResultFound:
            return None, "PROJECT"

    # type = (나머지) - db 조회를 통해서 생성/수정 알아내야함
    else:
        if request.file_type in (FileType.prd, FileType.userstory, FileType.srs):
            doc_type = request.file_type.value.upper()
            file = (db.query(Document)
                    .filter(
                Document.author_id == user_id,
                Document.project_id == request.project_id,
                Document.type == doc_type
            ).one_or_none())
            return file, doc_type

        elif request.file_type is FileType.task: # task일 경우
            """
                작성해야됨
            """
            file = None
            temp_type = "TASK"
            return file, temp_type

        else:
            raise _http_400(f"Unsupported file_type: {request.file_type}")


def create_file_repo(
    user_id: str, request: ChatSessionCreateRequest, db: Session
) -> tuple[Any, str]:

    if request.file_type is FileType.project:
        file = Project(
            title="New Project",
            owner_id=user_id,
            status="in_progress"
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
        proj = db.query(Project).filter(
            Project.owner_id == user_id,
            Project.id == request.project_id
        ).one_or_none()
        if proj is None:
            raise _http_404(f"Project(id={request.project_id}) not found or no permission.")

        file = Document(
            project_id=request.project_id,
            title=f"New {doc_type} Document",
            author_id=user_id,
            type=doc_type
        )
        try:
            db.add(file)
            _flush_and_refresh(db, file)
            return file, doc_type
        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to create document: {str(e)}")

    elif request.file_type is FileType.task:
        # 자동생성 정책이 명확하지 않아 차단
        raise _http_400("Task auto-creation is not supported here. Use Task API.")

    else:
        raise _http_400(f"Unsupported file_type: {request.file_type}")



def store_chat_session_repo(chat: ChatSession, db: Session) -> ChatSession:
    try:
        db.add(chat)
        return _flush_and_refresh(db, chat)
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Failed to create chat session: {str(e)}")
