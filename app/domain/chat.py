import time
import uuid
from typing import Any, Tuple, Iterator

from sqlalchemy.orm import Session

from app.db.models import ChatMessage, ChatSession, Project, Document, Task
from app.schemas.chat import ChatSessionCreateRequest, FileType


def fake_sync_llm(txt: str) -> Iterator[str]:
    # 실제 LLM 호출 대신 토막 응답을 동기적으로 생성
    chunks = [
        f"안녕하세요! 요청 요약: {txt[:60]}",
        "  → 동기 SSE 데모입니다.",
        "  → 비동기 없이도 1인용 스트리밍은 됩니다.",
        "  → 운영 확장성은 낮아요.",
        "끝!"
    ]
    for ch in chunks:
        # event-stream 한 프레임씩 밀어내기
        yield f"data: {ch}\n\n"
        time.sleep(0.2)  # 동기 대기(데모용)


######################################### SERVICE #############################################
def create_chat_session_with_message_service(user_id: str, request: ChatSessionCreateRequest, db: Session):
    file, file_type = create_and_check_file_id(user_id, request, db)

    # chat session 생성, file_id 결합 - chat id 반환
    chat_session = create_chat_session(user_id, file, file_type, db)

    # file(생성) 상위 file content를 chat message에 미리 등록, cf) Project -> 입력X, userstory -> project, prd 내용 등록
    # file(수정) 자신을 포함한 상위 file content를 chat message에 미리 등록, cf) Project -> Project, userstory -> project, prd, userstory 내용 등록
    attached_info_to_chat(user_id, chat_session.chat_id, file, file_type, db)

    # client채팅 추가()
    user_chat = create_chat_message(user_id, chat_session.chat_id, "user", request.content_md, db)
    chat_session = ChatSession(stream_url= "/api/v1/chats/" + chat_session.chat_id + "/stream")
    return chat_session






######################################### REPO #############################################


def attached_info_to_chat(user_id: str, chat_session_id: int, file: Any, file_type: str, db: Session) -> None:
    # 문서 내용 작성
    if file.content_md is None:
        if file_type == "PROJECT":
            return None
        project_content_md = select_file_info_repo(user_id, file.project_id.value(), "PROJECT", db)
        create_chat_message(user_id, chat_session_id, "System", project_content_md, db)

        if file.type.value().upper() == "PRD":
            return None
        prd_content_md = select_file_info_repo(user_id, file, "PRD", db)
        create_chat_message(user_id, chat_session_id, "System", prd_content_md, db)
        if file.type.value().upper() == "USERSTORY":
            return None
        user_story_content_md = select_file_info_repo(user_id, file, "USERSTORY", db)
        create_chat_message(user_id, chat_session_id, "System", user_story_content_md, db)
        if file.type.value().upper() == "SRS":
            return None
        srs_content_md = select_file_info_repo(user_id, file, "SRS", db)
        create_chat_message(user_id, chat_session_id, "System", srs_content_md, db)
        return None

    # 문서 내용 수정
    else:
        project_content_md = select_file_info_repo(user_id, file.project_id.value(), "PROJECT", db)
        create_chat_message(user_id, chat_session_id, "System", project_content_md, db)
        if file_type == "PROJECT":
            return None

        prd_content_md = select_file_info_repo(user_id, file, "PRD", db)
        create_chat_message(user_id, chat_session_id, "System", prd_content_md, db)
        if file.type.value().upper() == "PRD":
            return None

        user_story_content_md = select_file_info_repo(user_id, file, "USERSTORY", db)
        create_chat_message(user_id, chat_session_id, "System", user_story_content_md, db)
        if file.type.value().upper() == "USERSTORY":
            return None

        srs_content_md = select_file_info_repo(user_id, file, "SRS", db)
        create_chat_message(user_id, chat_session_id, "System", srs_content_md, db)
        if file.type.value().upper() == "SRS":
            return None

        srs_content_md = select_file_info_repo(user_id, file, "TASK", db)
        create_chat_message(user_id, chat_session_id, "System", srs_content_md, db)
        return None

def create_chat_message(user_id: str, chat_session_id: int, role: str, content: str, db: Session) -> ChatMessage:
    chat_message = ChatMessage(user_id = user_id, session_id = chat_session_id, role = role, content = content)
    chat_message = create_chat_message_repo(chat_message, db)
    db.commit()
    return chat_message

def create_and_check_file_id(user_id: str, request: ChatSessionCreateRequest, db: Session) -> Tuple[Any, str]:
    # 파일 존재 확인
    file, file_type = check_file_exist_repo(user_id, request, db)

    # 없으면 생성
    if file is None:
        file, file_type = create_file_repo(user_id, request, db)

    db.commit()
    return file, file_type

def create_chat_session(user_id: str, file: Any, file_type:str, db: Session) -> ChatSession:
    chat_session = check_chat_session(user_id, file, file_type, db)
    # 이미 파일과 관련된 채팅 세션 있음
    if chat_session:
        # 1. 문서 생성하고 내용 작성 X(이어서 하는 경우) -> chat session 그대로 사용
        if file.content_md == None:
            return chat_session


    # 2. 문서 생성하고 내용 작성 O(수정하는 경우) -> chat session 새로 열기
    # 3. 채팅 세션 존재하지 않는 경우
    chat_session = ChatSession(
        owner_id=user_id,
        file_id=file.id,
        file_type=file_type,
    )
    store_chat_session_repo(chat_session, db)
    db.commit()

    return chat_session




######################################### REPO #############################################

def check_chat_session(user_id: str, file: Any, file_type:str, db: Session) -> ChatSession:
    data = db.query(ChatSession).filter(ChatSession.user_id == user_id, ChatSession.file_type == file_type, ChatSession.file_id == file.id).one_or_none()
    return data

def select_file_info_repo(user_id: str, project_id: int, detail_type: str, db: Session) -> Any:
    if detail_type == "PROJECT":
        file = db.query(Project).filter(Project.owner_id == user_id, Project.id == project_id).one()
        return file.content_md

    elif detail_type in ["PRD, USERSTORY, SRS"]:
        file = db.query(Document).filter(Document.author_id == user_id, Document.project_id == project_id, Document.type == detail_type).one()
        return file

    elif detail_type == "TASK":
        pass

def create_chat_message_repo(chat_message: ChatMessage, db: Session) -> ChatMessage:
    db.add(chat_message)
    db.refresh(chat_message)
    return chat_message



def check_file_exist_repo(user_id: str, request: ChatSessionCreateRequest, db: Session) -> Tuple[Any, str] | Tuple[None, None]:
    # request body의 project id와 file_type 조합으로 유무 판별

    file_type: FileType = request.file_type
    project_id = request.project_id

    # Project Not Exist
    if project_id is None:
        return None, None

    file = None
    temp_type: str = None

    if file_type is FileType.project:
        file = db.query(Project).filter(Project.owner_id == user_id, Project.id == project_id).one_or_none()
        temp_type = "PROJECT"
    elif file_type in (FileType.prd, FileType.userstory, FileType.srs):
        file = db.query(Document).filter(Document.author_id == user_id, Document.id == project_id, Document.type == file_type.value.upper()).one_or_none()
        temp_type = file_type.value.upper()
    elif file_type is FileType.task: # task일 경우
        file = db.query(Task).filter(Task.assignee_id == user_id, Task.id == project_id).one_or_none()
        temp_type = "TASK"


    return file, temp_type

def create_file_repo(user_id: str, request: ChatSessionCreateRequest, db: Session) -> Tuple[Any, str]:
    file_type: FileType = request.file_type
    project_id = request.project_id
    file = None
    temp_type: str = None

    if file_type is FileType.project:
        file = Project(
            title="New Project",
            owner_id=user_id,
            status="in_progress"
        )
        temp_type = "PROJECT"
    elif file_type is FileType.task: # task일 경우
        temp_type = "TASK"
        pass
    elif file_type in (FileType.prd, FileType.userstory, FileType.srs):
        doc_type = file_type.value.upper()
        file = Document(
            project_id=project_id,
            title=f"New {doc_type} Document",
            author_id=user_id,
            type=doc_type.upper()
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