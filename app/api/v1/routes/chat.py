from fastapi import APIRouter, Depends,  Header
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.domain.chat import create_chat_session_with_message_service
from app.schemas.chat import ChatSessionCreateRequest, ChatSessionCreateResponse

SESSION_QUEUES: dict[str, asyncio.Queue[str]] = {}
SESSION_TASKS: dict[str, asyncio.Task] = {}

router = APIRouter(prefix="/chats", tags=["chats"])

# chat 시작 & init_project 생성
@router.post("", response_model=ChatSessionCreateResponse, status_code=201)
def start_chat_with_init_file(user_id: Header(..., alias="X-User-ID"), request: ChatSessionCreateRequest, db: Session = Depends(get_db)):
    return create_chat_session_with_message_service(user_id, request, db)

# SSE 연결, AI 응답 보내기
@router.GET("chats/{chat_session_id}/stream")
def stream_ai_message(chat_session_id: str):
    async def event_generator():

    # AI응답, chat message DB에 저장

    # AI 응답 -> client




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
