from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


# 공통 Base
class DocumentBase(BaseModel):
    title: str
    type: Literal['PRD', 'USER_STORY', 'SRS']

# 요청 DTO
class DocumentCreateRequest(DocumentBase):
    content_md: str

# 단일 응답 DTO (공통 응답)
class DocumentRead(BaseModel):
    id: int
    project_id: int
    type : Literal['PRD', 'USER_STORY', 'SRS']
    title: str
    content_md : str | None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class DocumentUpdateRequest(BaseModel):
    title: str | None = None
    content_md: str | None

class DocumentPage(BaseModel):
    documents: list[DocumentRead]
    model_config = ConfigDict(populate_by_name=True)
