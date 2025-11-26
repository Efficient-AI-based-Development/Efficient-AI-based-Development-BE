# ai_module/chains/task_ai_chain.py

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from ai_module.common.llm import get_llm, with_structured
from ai_module.common.prompts import task_ai_system
from app.schemas.ai import Task, TaskAIOutput


def create_task_modify_chain() -> Runnable:
    """
    기존 Task 수정용 체인.
    """
    llm = with_structured(get_llm("task_ai", temperature=0.3), TaskAIOutput)
    system_prompt = task_ai_system()
    human_prompt = (
        "=== 현재 Task 정보 ===\n"
        "Task ID: {task_id}\n"
        "제목: {title}\n"
        "설명: {description}\n"
        "역할: {assigned_role}\n"
        "우선순위: {priority}\n"
        "태그: {tag}\n\n"
        "=== 사용자 수정 요청 ===\n"
        "{user_feedback}\n\n"
        "위 피드백을 반영하여 Task를 수정해주세요. "
        "변경된 내용을 changes 배열에 명확히 기록하세요."
    )
    prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", human_prompt)])
    return prompt | llm


def create_task_add_chain() -> Runnable:
    """
    새 Task 추가용 체인.
    """
    llm = with_structured(get_llm("task_ai", temperature=0.3), TaskAIOutput)
    system_prompt = task_ai_system()
    human_prompt = (
        "=== 기존 Task 목록 ===\n"
        "{existing_tasks}\n\n"
        "=== 프로젝트 컨텍스트 ===\n"
        "{project_context}\n\n"
        "=== 사용자 추가 요청 ===\n"
        "{user_request}\n\n"
        "위 요청을 바탕으로 새로운 Task를 생성해주세요. "
        "기존 Task ID와 중복되지 않도록 적절한 ID를 부여하고, "
        "기존 Task들과 일관된 스타일로 작성하세요."
    )
    prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", human_prompt)])
    return prompt | llm


def modify_task(current_task: Task, user_feedback: str) -> TaskAIOutput:
    """
    기존 Task를 사용자 피드백에 따라 수정한다.
    """
    chain = create_task_modify_chain()
    result = chain.invoke(
        {
            "task_id": current_task.task_id,
            "title": current_task.title,
            "description": current_task.description,
            "assigned_role": current_task.assigned_role,
            "priority": current_task.priority,
            "tag": current_task.tag,
            "user_feedback": user_feedback,
        }
    )

    if isinstance(result, TaskAIOutput):
        return result
    if isinstance(result, dict):
        return TaskAIOutput(**result)

    # 폴백
    return TaskAIOutput(
        task=current_task,
        changes=["수정 실패"],
        message="Task 수정 중 오류가 발생했습니다.",
    )


def add_task(
    existing_tasks: list[Task],
    user_request: str,
    project_context: str | None = None,
) -> TaskAIOutput:
    """
    새로운 Task를 생성한다.
    """
    chain = create_task_add_chain()

    # 기존 Task 목록을 문자열로 변환
    tasks_str = "\n".join(
        [f"- Task {t.task_id}: {t.title} ({t.assigned_role}, priority={t.priority}, tag={t.tag})" for t in existing_tasks]
    )

    result = chain.invoke(
        {
            "existing_tasks": tasks_str or "없음",
            "project_context": project_context or "별도 컨텍스트 없음",
            "user_request": user_request,
        }
    )

    if isinstance(result, TaskAIOutput):
        return result
    if isinstance(result, dict):
        return TaskAIOutput(**result)

    # 폴백 - 기본 Task 생성
    max_id = max([t.task_id for t in existing_tasks], default=0)
    fallback_task = Task(
        task_id=max_id + 1,
        title="새 Task",
        description=user_request,
        assigned_role="Backend",
        priority=5,
        tag="개발",
    )

    return TaskAIOutput(
        task=fallback_task,
        changes=["새 Task 생성"],
        message="Task 생성 중 오류가 발생했지만 기본 Task를 생성했습니다.",
    )
