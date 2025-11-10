"""Chat-related Pydantic schemas."""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

class FileType(str, Enum):
    project = "PROJECT"
    prd = "PRD"
    userstory = "USER_STORY"
    srs = "SRS"
    task = "TASK"

class ChatMessageRequest(BaseModel):
    content_md: str

class ChatSessionCreateRequest(ChatMessageRequest):
    file_type: FileType
    project_id: int

class ChatSessionCreateResponse(BaseModel):
    chat_id: int
    stream_url: str
    file_type: FileType
    project_id: int
    created_at: datetime

class StoreFileRequest(BaseModel):
    project_id: int


class StoreFileResponse(BaseModel):
    ok: bool
    file_type: str
    file_id: int
    updated_at: datetime
