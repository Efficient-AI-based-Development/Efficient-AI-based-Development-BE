# ai_module/chains/pm_chain.py

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from ai_module.common.llm import get_llm, with_structured
from ai_module.common.prompts import pm_system
from app.schemas.ai import PMAgentOutput, ProjectMetadata


def create_pm_agent_chain() -> Runnable:
    """
    PM Agent 초기 프로젝트 메타데이터 추출용 체인.
    - user_input: 사용자의 프로젝트 설명
    """
    llm = with_structured(get_llm("pm", temperature=0.3), PMAgentOutput)
    system_prompt = pm_system()
    human_prompt = (
        "사용자가 다음과 같이 프로젝트를 설명했습니다:\n\n"
        "{user_input}\n\n"
        "위 내용을 분석하여 프로젝트 메타데이터를 추출하고, "
        "부족한 정보는 서비스 특성에 맞게 제안해주세요."
    )
    prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", human_prompt)])
    return prompt | llm


def create_pm_chat_chain() -> Runnable:
    """
    PM Agent 대화형 수정용 체인.
    - current_metadata: 현재 프로젝트 메타데이터
    - user_feedback: 사용자의 수정 요청
    """
    llm = with_structured(get_llm("pm", temperature=0.3), PMAgentOutput)
    system_prompt = pm_system()
    human_prompt = (
        "=== 현재 프로젝트 메타데이터 ===\n"
        "프로젝트명: {project_name}\n"
        "메인 컬러: {main_color}\n"
        "페이지 수: {page_count}\n"
        "기능 수: {feature_count}\n"
        "AI 모델: {ai_model}\n"
        "기술 스택: {tech_stack}\n"
        "서비스 설명: {service_description}\n\n"
        "=== 사용자 피드백 ===\n"
        "{user_feedback}\n\n"
        "위 피드백을 반영하여 프로젝트 메타데이터를 수정해주세요."
    )
    prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", human_prompt)])
    return prompt | llm


def generate_pm_metadata(user_input: str) -> PMAgentOutput:
    """
    초기 프로젝트 메타데이터를 생성한다.
    """
    chain = create_pm_agent_chain()
    result = chain.invoke({"user_input": user_input})

    if isinstance(result, PMAgentOutput):
        return result
    if isinstance(result, dict):
        return PMAgentOutput(**result)

    # 폴백
    return PMAgentOutput(
        metadata=ProjectMetadata(
            project_name="Unknown Project",
            main_color="#3498db",
            page_count=5,
            feature_count=3,
            ai_model="Solar-Pro",
            tech_stack=[
                "React",
                "TypeScript",
                "FastAPI",
                "Python",
                "PostgreSQL",
                "Docker",
            ],
            service_description=user_input,
        ),
        summary="프로젝트 메타데이터 추출에 실패했습니다.",
        suggestions=["다시 시도해주세요."],
        message="PM Agent 처리 중 오류가 발생했습니다.",
    )


def update_pm_metadata(current_metadata: ProjectMetadata, user_feedback: str) -> PMAgentOutput:
    """
    사용자 피드백을 반영하여 프로젝트 메타데이터를 수정한다.
    """
    chain = create_pm_chat_chain()
    result = chain.invoke(
        {
            "project_name": current_metadata.project_name,
            "main_color": current_metadata.main_color,
            "page_count": current_metadata.page_count,
            "feature_count": current_metadata.feature_count,
            "ai_model": current_metadata.ai_model,
            "tech_stack": ", ".join(current_metadata.tech_stack),
            "service_description": current_metadata.service_description,
            "user_feedback": user_feedback,
        }
    )

    if isinstance(result, PMAgentOutput):
        return result
    if isinstance(result, dict):
        return PMAgentOutput(**result)

    # 폴백
    return PMAgentOutput(
        metadata=current_metadata,
        summary="메타데이터 수정에 실패했습니다.",
        suggestions=["다시 시도해주세요."],
        message="PM Agent 처리 중 오류가 발생했습니다.",
    )
