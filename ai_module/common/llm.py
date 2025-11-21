# ai_module/common/llm.py

from __future__ import annotations

import json

from langchain_community.chat_models import FakeListChatModel
from langchain_core.language_models import BaseChatModel
from langchain_upstage import ChatUpstage
from pydantic import BaseModel

from app.core.config import settings
from app.utils.logger import get_logger

DEFAULT_MODEL = "solar-pro2"
logger = get_logger(__name__)


# 프롬프트에 따라 사용할 LLM 모델 결정
def get_model_name(kind: str | None = None) -> str:
    if kind == "prd":
        return getattr(settings, "LLM_MODEL_PRD", DEFAULT_MODEL) or DEFAULT_MODEL
    if kind == "tasklist":
        return getattr(settings, "LLM_MODEL_TASKLIST", DEFAULT_MODEL) or DEFAULT_MODEL
    if kind == "planner":
        return getattr(settings, "LLM_MODEL_DECOMPOSER", DEFAULT_MODEL) or DEFAULT_MODEL
    if kind == "auditor":
        return getattr(settings, "LLM_MODEL_AUDITOR", DEFAULT_MODEL) or DEFAULT_MODEL
    if kind == "writer":
        return getattr(settings, "LLM_MODEL_WRITER", DEFAULT_MODEL) or DEFAULT_MODEL
    if kind == "userstory":
        return getattr(settings, "LLM_MODEL_USERSTORY", DEFAULT_MODEL) or DEFAULT_MODEL
    return getattr(settings, "LLM_MODEL_SOLAR", DEFAULT_MODEL) or DEFAULT_MODEL


# ChatUpStage 인스턴스 생성
def get_llm(
    kind: str | None = None,
    temperature: float = 0.25,
    top_p: float = 0.9,
    max_tokens: int = 2500,
    mock_response: str | None = None,
) -> BaseChatModel:
    name = get_model_name(kind)

    if not settings.UPSTAGE_API_KEY:
        logger.warning("[LLM] API Key 미설정 — Mock LLM 사용 (model=%s)", name)
        return FakeListChatModel(
            responses=[mock_response or json.dumps({"ok": True})],
            name=f"MOCK-{name}",
        )

    logger.info(
        "[LLM] 초기화 (model=%s, kind=%s, temp=%.2f, top_p=%.2f, max_tokens=%d)",
        name,
        kind,
        temperature,
        top_p,
        max_tokens,
    )

    return ChatUpstage(
        model=name,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        upstage_api_key=settings.UPSTAGE_API_KEY,
    )


# LLM 출력이 JSON으로 오도록 래핑
def with_structured(llm: BaseChatModel, schema: type[BaseModel]) -> BaseChatModel:
    logger.debug(
        "[LLM] 구조화 출력 활성화 (schema=%s)",
        getattr(schema, "__name__", str(schema)),
    )
    return llm.with_structured_output(schema)
