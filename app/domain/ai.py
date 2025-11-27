from fastapi import HTTPException

from ai_module.chains.pm_chain import (
    generate_pm_metadata,
    update_pm_metadata,
)
from ai_module.chains.prd_chain import (
    create_prd_chat_chain,
    generate_prd,
)
from ai_module.chains.srs_chain import (
    create_srs_chat_chain,
    generate_srs,
)
from ai_module.chains.task_ai_chain import (
    add_task,
)
from ai_module.chains.tasklist_chain import generate_tasklist
from ai_module.chains.userstory_chain import (
    create_userstory_chat_chain,
    generate_userstory,
)
from app.schemas.ai import (
    PMAgentOutput,
    ProjectMetadata,
    TaskAddInput,
    TaskAIOutput,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


# PRD 생성 API 엔드포인트
async def generate_prd_endpoint(user_input: str) -> str:
    try:
        logger.info("[PRD] 요청 수신")
        logger.debug("[PRD] 입력 미리보기: %s", user_input[:120])
        prd = generate_prd(user_input)
        logger.info("[PRD] 문서 생성 완료 (길이=%d)", len(prd.prd_document or ""))
        return prd
    except Exception as e:
        logger.exception("[PRD] 오류 발생: %s", e)
        raise HTTPException(status_code=500, detail=f"PRD 서버 오류: {e}")


async def prd_chat(
    prd_document: str,
    user_feedback: str,
) -> str:
    try:
        logger.info("[PRD-CHAT] 요청 수신")
        logger.debug(
            "[PRD-CHAT] 사용자 요청 미리보기: %s",
            user_feedback[:120] if user_feedback else "",
        )

        chain = create_prd_chat_chain()
        result = chain.invoke({"prd_document": prd_document, "user_feedback": user_feedback})

        logger.info(
            "[PRD-CHAT] 수정 완료 (길이=%d)",
            len(getattr(result, "prd_document", "") or ""),
        )
        return result
    except Exception as e:
        logger.exception("[PRD-CHAT] 오류 발생: %s", e)
        raise HTTPException(status_code=500, detail=f"PRD Chat 서버 오류: {e}")


async def generate_srs_endpoint(user_input: str) -> str:
    try:
        logger.info("[SRS] 요청 수신")
        logger.debug("[SRS] 입력 미리보기: %s", user_input[:120])
        srs = generate_srs(user_input)
        logger.info("[SRS] 문서 생성 완료 (길이=%d)", len(srs.srs_document or ""))
        return srs
    except Exception as e:
        logger.exception("[SRS] 오류 발생: %s", e)
        raise HTTPException(status_code=500, detail=f"SRS 서버 오류: {e}")


# SRS 문서 대화형 생성/수정 API 엔드포인트
async def srs_chat(
    srs_document: str,
    user_feedback: str,
) -> str:
    try:
        logger.info("[SRS-CHAT] 요청 수신")
        logger.debug(
            "[SRS-CHAT] 사용자 요청 미리보기: %s",
            user_feedback[:120] if user_feedback else "",
        )

        chain = create_srs_chat_chain()
        result = chain.invoke({"srs_document": srs_document, "user_feedback": user_feedback})

        logger.info(
            "[SRS-CHAT] 수정 완료 (길이=%d)",
            len(getattr(result, "srs_document", "") or ""),
        )
        return result
    except Exception as e:
        logger.exception("[SRS-CHAT] 오류 발생: %s", e)
        raise HTTPException(status_code=500, detail=f"SRS Chat 서버 오류: {e}")


async def generate_userstory_endpoint(user_input: str) -> str:
    try:
        logger.info("[USERSTORY] 요청 수신")
        logger.debug("[USERSTORY] 입력 미리보기: %s", user_input[:120])
        us = generate_userstory(user_input)
        logger.info(
            "[USERSTORY] 문서 생성 완료 (길이=%d)",
            len(us.user_story or ""),
        )
        return us
    except Exception as e:
        logger.exception("[USERSTORY] 오류 발생: %s", e)
        raise HTTPException(status_code=500, detail=f"User Story 서버 오류: {e}")


# User Story 대화형 생성/수정 API 엔드포인트
async def userstory_chat(
    user_story: str,
    user_feedback: str,
) -> str:
    try:
        logger.info("[USERSTORY-CHAT] 요청 수신")
        logger.debug(
            "[USERSTORY-CHAT] 사용자 요청 미리보기: %s",
            user_feedback[:120] if user_feedback else "",
        )

        chain = create_userstory_chat_chain()
        result = chain.invoke({"user_story": user_story, "user_feedback": user_feedback})

        logger.info(
            "[USERSTORY-CHAT] 수정 완료 (길이=%d)",
            len(getattr(result, "user_story", "") or ""),
        )
        return result
    except Exception as e:
        logger.exception("[USERSTORY-CHAT] 오류 발생: %s", e)
        raise HTTPException(status_code=500, detail=f"User Story Chat 서버 오류: {e}")


# Task List 생성 API 엔드포인트
async def generate_tasklist_endpoint(prd_document: str | None = None, user_input: str | None = None) -> str:
    try:
        logger.info("[TaskList] 요청 수신")
        logger.debug("[TaskList] 입력 미리보기: %s", user_input[:120])
        md = generate_tasklist(
            prd_document=prd_document,
            user_input=user_input,
        )
        logger.info("[TaskList] 생성 완료")
        return md
    except Exception as e:
        logger.exception("[TaskList] 오류 발생: %s", e)
        raise HTTPException(status_code=500, detail=f"Task List 서버 오류: {e}")


# PM Agent 초기 메타데이터 추출 API 엔드포인트
async def pm_agent_endpoint(user_input: str) -> str:
    try:
        logger.info("[PM-Agent] 요청 수신")
        logger.debug("[PM-Agent] 입력: %s", user_input[:120])
        result = generate_pm_metadata(user_input)
        logger.info(
            "[PM-Agent] 메타데이터 추출 완료 (프로젝트명=%s)",
            result.metadata.project_name,
        )
        return result
    except Exception as e:
        logger.exception("[PM-Agent] 오류 발생: %s", e)
        raise HTTPException(status_code=500, detail=f"PM Agent 서버 오류: {e}")


# PM Agent 대화형 수정 API 엔드포인트
async def pm_agent_chat(current_metadata: ProjectMetadata, user_feedback: str) -> PMAgentOutput:
    try:
        logger.info("[PM-Agent-Chat] 요청 수신")
        logger.debug("[PM-Agent-Chat] 피드백: %s", user_feedback[:120])
        result = update_pm_metadata(current_metadata, user_feedback)
        logger.info(
            "[PM-Agent-Chat] 메타데이터 수정 완료 (프로젝트명=%s)",
            result.metadata.project_name,
        )
        return result
    except Exception as e:
        logger.exception("[PM-Agent-Chat] 오류 발생: %s", e)
        raise HTTPException(status_code=500, detail="PM Agent Chat 서버 오류: %e")


async def task_add_endpoint(task_input: TaskAddInput) -> TaskAIOutput:
    try:
        logger.info("[Task-AI-Add] 요청 수신 (existing_tasks=%d)", len(task_input.existing_tasks))
        logger.debug("[Task-AI-Add] 요청: %s", task_input.user_request[:120])
        result = add_task(
            task_input.existing_tasks,
            task_input.user_request,
            task_input.project_context,
        )
        logger.info(
            "[Task-AI-Add] Task 추가 완료 (new_task_id=%s, title=%s)",
            result.task.task_id,
            result.task.title,
        )
        return result
    except Exception as e:
        logger.exception("[Task-AI-Add] 오류 발생: %s", e)
        raise HTTPException(status_code=500, detail="Task Add 서버 오류: %e")
