import asyncio
from typing import Any, Tuple, Iterator, List

from fastapi import HTTPException
from sqlalchemy.exc import NoResultFound, IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models import ChatMessage, Project, Document, ChatSession, Task
from app.schemas.chat import ChatSessionCreateRequest, ChatSessionCreateResponse, FileType

SESSION_IN = {}
SESSION_OUT = {}
SESSION_TASK = {}


async def ensure_worker(user_id: str, session_id: int, db: Session):
    if session_id in SESSION_TASK and not SESSION_TASK[session_id].done():
        return

    in_q = SESSION_IN.setdefault(session_id, asyncio.Queue())
    out_q = SESSION_OUT.setdefault(session_id, asyncio.Queue())

    async def worker():
        try:
            while True:
                user_message = await in_q.get()

                if not isinstance(user_message, str) or not user_message.strip():
                    # 큐에 잘못 들어온 경우는 로그로만 처리하고 skip
                    await out_q.put("[[END]]")
                    continue

                try:
                    db.add(ChatMessage(
                        session_id=session_id,
                        role="user",
                        content=user_message,
                        user_id=user_id
                    ))
                    _safe_commit(db)
                except HTTPException:
                    # 스트림은 끊지 않고 종료 신호만 보냄
                    await out_q.put("[[END]]")
                    continue

                assembled = []
                # fake ai streaming (비동기)
                for token in ["안녕 ", "나는 ", "AI ", "야 ", "!", "\n"]:
                    await asyncio.sleep(0.05)
                    assembled.append(token)
                    await out_q.put(token)

                # 한 턴 종료
                await out_q.put("[[END]]")

                full_text = "".join(assembled)
                try:
                    db.add(ChatMessage(
                        session_id=session_id,
                        role="assistant",
                        content=full_text,
                        user_id=user_id
                    ))
                    _safe_commit(db)
                except HTTPException:
                    # 저장 실패해도 워커는 유지
                    pass

        except asyncio.CancelledError:
            return

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
def create_chat_session_with_message_service(user_id: str, request: ChatSessionCreateRequest, db: Session):
    # 입력 검증
    if not user_id:
        raise _http_400("X-User-ID header required.")
    if request is None:
        raise _http_400("Request body is required.")

    # 파일 존재 O -> 불러오기, 파일 존재 X -> 파일 생성 후 불러오기
    file, file_type = create_and_check_file_id(user_id, request, db)

    # chat session 생성
    chat_session = create_chat_session(user_id, file, file_type, db)

    # file(생성) 상위 file content를 chat message에 미리 등록, cf) Project -> 입력X, userstory -> project, prd 내용 등록
    # file(수정) 자신을 포함한 상위 file content를 chat message에 미리 등록, cf) Project -> Project, userstory -> project, prd, userstory 내용 등록
    attached_info_to_chat(user_id, chat_session.id, file, file_type, db)

    # client채팅 추가()
    create_chat_message(user_id, chat_session.id, "user", request.content_md, db)

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
    project_content_md = insert_file_info_repo(user_id, file, file_type, db)
    chatMessage = ChatMessage(session_id=chat_session_id, role="system", user_id = user_id, content=project_content_md)
    create_chat_message_repo(chatMessage, db)
    db.commit()


def create_chat_message(user_id: str, chat_session_id: int, role: str, content: str, db: Session) -> ChatMessage:
    chat_message = ChatMessage(user_id = user_id, session_id = chat_session_id, role = role, content = content)
    chat_message = create_chat_message_repo(chat_message, db)
    db.commit()
    return chat_message

def create_and_check_file_id(user_id: str, request: ChatSessionCreateRequest, db: Session) -> Tuple[Any, str]:
    # project_id = -1 인 경우 -> 프로젝트 생성
    if request.project_id == -1:
        if request.file_type is FileType.project:
            file, file_type = create_file_repo(user_id, request, db)
        else:
            raise _http_400("project_id = -1 은 PROJECT 생성에만 사용할 수 있습니다. 문서/태스크는 기존 project_id가 필요합니다.")
    else: # 파일 존재 확인
        file, file_type = check_file_exist_repo(user_id, request, db)
        # file None이면 존재하지 않는 파일 (PRD/USER_STORY/SRS/TASK) -> 파일 생성
        if file is None:
            file, file_type = create_file_repo(user_id, request, db)

    db.commit()
    return file, file_type

def create_chat_session(user_id: str, file: Any, file_type:str, db: Session) -> ChatSession:
    if isinstance(file, Project):
        target_file_id = file.id
    elif isinstance(file, Document):
        target_file_id = file.id
    elif isinstance(file, Task):
        target_file_id = file.id
    else:
        raise TypeError(f"Unsupported file type: {type(file)}")
    chat_session = ChatSession(
        user_id=user_id,
        file_type=file_type,
        file_id=target_file_id,
    )
    store_chat_session_repo(chat_session, db)
    db.commit()
    return chat_session




######################################### REPO #############################################

def insert_file_info_repo(user_id: str, file: Any, file_type: str, db: Session) -> Any:
    parts: List[str] = []

    def _safe_append(text: Any):
        if text:
            parts.append(str(text))

    if isinstance(file, Project):
        proj = db.query(Project).filter(Project.owner_id == user_id, Project.id == file.id).one_or_none()
        if proj is None:
            raise NoResultFound(f"Project {getattr(file, 'id', None)} not found or no permission")
        _safe_append(getattr(proj, "content_md", ""))
        return "\n\n".join(parts)


    elif isinstance(file, Document):
        proj = db.query(Project).filter(Project.owner_id == user_id, Project.id == file.project_id).one_or_none()
        if proj is None:
            raise NoResultFound(f"Project {file.project_id} not found or no permission")
        _safe_append(getattr(proj, "content_md", ""))

        PRD = db.query(Document).filter(Document.author_id == user_id, Document.project_id == file.project_id, Document.type == "PRD").one_or_none()
        _safe_append(getattr(PRD, "content_md", ""))
        if file_type == "PRD":
            return "\n\n".join(parts)


        USER_STORY = db.query(Document).filter(Document.author_id == user_id, Document.project_id == file.project_id, Document.type == "USER_STORY").one_or_none()
        _safe_append(getattr(USER_STORY, "content_md", ""))
        if file_type == "USER_STORY":
            return "\n\n".join(parts)


        SRS = db.query(Document).filter(Document.author_id == user_id, Document.project_id == file.project_id, Document.type == "SRS").one_or_none()
        _safe_append(getattr(SRS, "content_md", ""))
        if file_type == "SRS":
            return "\n\n".join(parts)

    elif isinstance(file, Task):
        pass



def create_chat_message_repo(chat_message: ChatMessage, db: Session) -> ChatMessage:
    db.add(chat_message)
    db.flush()
    db.refresh(chat_message)
    return chat_message



def check_file_exist_repo(user_id: str, request: ChatSessionCreateRequest, db: Session) -> Tuple[Any, str] | Tuple[None, str]:
    # request body의 project id와 file_type 조합으로 유무 판별

    # type = project인 경우 project 수정임
    if request.file_type is FileType.project:
        file = db.query(Project).filter(Project.owner_id == user_id, Project.id == request.project_id).one()
        temp_type = "PROJECT"

    # type = (나머지) - db 조회를 통해서 생성/수정 알아내야함
    else:
        if request.file_type in (FileType.prd, FileType.userstory, FileType.srs):
            file = (db.query(Document)
                    .filter(Document.author_id == user_id
                            , Document.project_id == request.project_id
                            , Document.type == request.file_type.value.upper())
                    .one_or_none())
            temp_type = request.file_type.value.upper()

        elif request.file_type is FileType.task: # task일 경우
            file = db.query(Task).filter(Task.assignee_id == user_id, Task.id == request.project_id).one_or_none()
            temp_type = "TASK"


    return file, temp_type

def create_file_repo(user_id: str, request: ChatSessionCreateRequest, db: Session) -> Tuple[Any, str]:

    if request.file_type in FileType.project:
        file = Project(
            title="New Project",
            owner_id=user_id,
            status="in_progress"
        )
        temp_type = "PROJECT"
    elif request.file_type == FileType.task: # task일 경우
        temp_type = "TASK"
        pass
    elif request.file_type in (FileType.prd, FileType.userstory, FileType.srs):
        doc_type = request.file_type.value.upper()
        file = Document(
            project_id=request.project_id,
            title=f"New {doc_type} Document",
            author_id=user_id,
            type=doc_type
        )
        temp_type = doc_type

    db.add(file)
    db.flush()
    db.refresh(file)
    return file, temp_type

def store_chat_session_repo(chat: ChatSession, db: Session) -> ChatSession:
    db.add(chat)
    db.flush()
    db.refresh(chat)
    return chat