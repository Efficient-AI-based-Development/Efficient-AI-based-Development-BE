# ai_module/chains/srs_chain.py

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from ai_module.common.llm import get_llm, with_structured
from app.schemas.ai import SRSOutput


def create_srs_chat_chain() -> Runnable:
    """
    SRS 생성/수정용 대화형 체인.
    - srs_document: 기존 SRS (빈 문자열이면 새로 생성)
    - user_feedback: 수정 또는 생성 요청
    """
    llm = with_structured(get_llm("srs"), SRSOutput)
    system_prompt = (
        "당신은 SRS 작성 전문가입니다. 아래 기존 SRS와 사용자 요청을 참고하여 "
        "SRS를 생성/수정하세요. 반드시 SRSOutput 스키마에 맞는 JSON만 출력하고, "
        "message 필드에 안내 메시지를 작성하세요."
    )
    human_prompt = "=== 기존 SRS 내용 ===\n" "{srs_document}\n\n" "=== 사용자 요청 ===\n" "{user_feedback}\n\n"
    prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", human_prompt)])
    return prompt | llm


def generate_srs(user_input: str) -> SRSOutput:
    """
    초기 SRS 문서를 생성한다.
    - 기존 SRS는 없다고 가정하고, srs_document=\"\" 로 두고 user_input을 피드백처럼 전달.
    """
    chain = create_srs_chat_chain()
    result = chain.invoke(
        {
            "srs_document": "",
            "user_feedback": user_input,
        }
    )

    if isinstance(result, SRSOutput):
        return result
    if isinstance(result, dict) and "srs_document" in result:
        return SRSOutput(
            srs_document=result["srs_document"],
            message=result.get("message") or "SRS 초안을 생성했습니다.",
        )

    return SRSOutput(
        srs_document="# SRS 생성 실패",
        message="SRS 생성 중 오류가 발생했습니다.",
    )
