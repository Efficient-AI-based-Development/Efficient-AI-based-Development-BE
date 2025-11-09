"""Chat-related Pydantic schemas."""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

class FileType(str, Enum):
    project = "PROJECT"
    prd = "PRD"
    userstory = "USERSTORY"
    srs = "SRS"
    task = "TASK"

class ChatMessageRequest(BaseModel):
    content_md: str

class ChatSessionCreateRequest(ChatMessageRequest):
    file_type: FileType
    project_id: int | None = None

class ChatSessionCreateResponse(BaseModel):
    chat_id: int
    stream_url: str
    file_type: FileType
    file_id: int
    created_at: datetime
    updated_at: datetime | None = None