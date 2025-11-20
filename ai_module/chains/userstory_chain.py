# ai_module/chains/userstory_chain.py

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from ai_module.common.llm import get_llm, with_structured
from ai_module.common.prompts import userstory_system
from app.schemas.ai import UserStoryOutput


def create_userstory_chat_chain() -> Runnable:
    """
    User Story 생성/수정용 대화형 체인.
    - user_story: 기존 User Story (빈 문자열이면 새로 생성)
    - user_feedback: 수정 또는 생성 요청
    """
    llm = with_structured(get_llm("userstory", temperature=0.0), UserStoryOutput)
    system_prompt = userstory_system()
    human_prompt = "=== 기존 User Story 내용 ===\n" "{user_story}\n\n" "=== 사용자 요청 ===\n" "{user_feedback}\n\n"
    prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", human_prompt)])
    return prompt | llm


def generate_userstory(user_input: str) -> UserStoryOutput:
    """
    초기 User Story 문서를 생성한다.
    - 기존 User Story는 없다고 가정하고, user_story=\"\" 로 두고 user_input을 피드백처럼 전달.
    """
    chain = create_userstory_chat_chain()
    result = chain.invoke(
        {
            "user_story": "",
            "user_feedback": user_input,
        }
    )

    if isinstance(result, UserStoryOutput):
        return result
    if isinstance(result, dict) and "user_story" in result:
        return UserStoryOutput(
            user_story=result["user_story"],
            message=result.get("message") or "User Story 초안을 생성했습니다.",
        )

    return UserStoryOutput(
        user_story="# User Story 생성 실패",
        message="User Story 생성 중 오류가 발생했습니다.",
    )
