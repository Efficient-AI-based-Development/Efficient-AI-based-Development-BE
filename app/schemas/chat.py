"""Chat-related Pydantic schemas."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class ChatMessageCreate(BaseModel):
    """채팅 메시지 생성 요청 스키마
    
    POST /api/chats/{chatID}/messages 요청 시 사용
    """
    content: str = Field(..., description="메시지 내용")
    role: str = Field(
        default="user",
        description="메시지 역할",
        examples=["user", "assistant", "system"]
    )


class ChatMessageResponse(BaseModel):
    """채팅 메시지 응답 스키마"""
    id: int
    chat_id: int
    content: str
    role: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ChatSessionCreate(BaseModel):
    """채팅 세션 생성 요청 스키마
    
    POST /api/v1/docs/{docID}/chats 요청 시 사용
    """
    doc_id: int = Field(..., description="문서 ID")
    title: Optional[str] = Field(None, description="채팅 세션 제목")


class ChatSessionResponse(BaseModel):
    """채팅 세션 응답 스키마"""
    id: int
    doc_id: int
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ChatListResponse(BaseModel):
    """채팅 세션 목록 응답 스키마"""
    items: List[ChatSessionResponse]
    total: int = Field(..., description="전체 세션 수")

