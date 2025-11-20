# ai_module/chains/prd_chain.py

from __future__ import annotations

import json

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from ai_module.common.llm import get_llm, with_structured
from ai_module.common.prompts import prd_system
from app.schemas.ai import PRDOutput


# PRD 초안 생성을 위한 LLM 파이프라인
def create_prd_generation_chain() -> Runnable:
    llm = with_structured(get_llm("prd"), PRDOutput)
    system_template = prd_system()
    human_prompt = "제품 요구사항 입력: {user_input}"

    prompt = ChatPromptTemplate.from_messages([("system", system_template), ("human", human_prompt)])

    # 지금은 schema_text 안 쓰지만, 필요하면 프롬프트에 넣을 때 활용 가능
    _schema_text = json.dumps(PRDOutput.model_json_schema(), ensure_ascii=False, indent=2)
    return prompt | llm


# PRD 문서 생성
def generate_prd(user_input: str) -> PRDOutput:
    chain = create_prd_generation_chain()
    result = chain.invoke({"user_input": user_input})

    if isinstance(result, PRDOutput):
        return result
    if isinstance(result, dict):
        return PRDOutput(**result)

    return PRDOutput(
        prd_document="# PRD 생성 실패",
        message="PRD 생성 중 오류가 발생했습니다.",
    )


# PRD 문서 생성 및 수정 LLM 체인
def create_prd_chat_chain() -> Runnable:
    llm = with_structured(get_llm("prd"), PRDOutput)
    system_prompt = prd_system()
    human_prompt = (
        "다음은 PRD 문서 작성/수정 요청입니다.\n\n"
        "=== 기존 PRD 내용 ===\n"
        "{prd_document}\n\n"
        "=== 사용자 요청 ===\n"
        "{user_feedback}\n\n"
        "위 정보를 바탕으로, 반드시 PRDOutput 스키마에 맞는 JSON만 출력하세요.\n"
        "또한, 변경된 문서와 함께 사용자 요청에 대한 안내 메시지를 message 필드에 한국어로 작성하세요."
    )
    prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", human_prompt)])
    return prompt | llm
