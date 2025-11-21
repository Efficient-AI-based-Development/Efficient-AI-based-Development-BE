# ai_module/graphs/decomposition_graph.py

import json

from langgraph.graph import END
from langgraph.graph.state import StateGraph

from app.utils.logger import get_logger

from .agents.auditor_agent import create_auditor_chain
from .agents.planner_agent import create_planner_chain
from .agents.writer_agent import create_writer_chain
from .state import GraphState

logger = get_logger(__name__)

# 그래프 내에서 사용할 기본 Task ID
DEFAULT_TASK_ID = "TASK-BE-001"


# Planner 노드: 상위 Task 설명을 SubTask 리스트로 분해
def planner_node(state: GraphState) -> GraphState:
    logger.info("[PLANNER] start")
    parent_task = state["user_input"]
    if state.get("feedback_message"):
        logger.debug("[PLANNER] refinement feedback: %s", state["feedback_message"])

    chain = create_planner_chain()
    new_retry = state.get("retry_count", 0) + 1

    try:
        result = chain.invoke(
            {
                "parent_task_id": DEFAULT_TASK_ID,
                "task_description": parent_task,
                "feedback": state.get("feedback_message", ""),
            }
        )
        subtasks_list = [t.model_dump() for t in result.subtasks]
        logger.info("[PLANNER] 생성된 SubTask 수: %d", len(subtasks_list))
        return {
            "subtasks": subtasks_list,
            "status": "REVIEW_NEEDED",
            "feedback_message": f"Planner 성공: SubTask {len(subtasks_list)}개 생성.",
            "retry_count": new_retry,
        }
    except Exception as e:
        logger.exception("[PLANNER] error: %s", e)
        return {
            "subtasks": state.get("subtasks", []),
            "status": "ERROR",
            "feedback_message": f"Planner 오류: {e}",
            "retry_count": new_retry,
        }


# Auditor 노드: 생성된 SubTask 리스트를 검증하고 PASS/REFINEMENT 판단
def auditor_node(state: GraphState) -> GraphState:
    logger.info("[AUDITOR] start")
    chain = create_auditor_chain()
    subtasks_json = json.dumps(state["subtasks"], ensure_ascii=False, indent=2)
    try:
        result = chain.invoke(
            {
                "parent_task_description": state["user_input"],
                "subtasks_json": subtasks_json,
            }
        )
        logger.info("[AUDITOR] 판단: %s", result.next_action)
        logger.debug("[AUDITOR] feedback: %s", result.feedback)
        return {
            "subtasks": state["subtasks"],
            "status": result.next_action,
            "feedback_message": result.feedback,
        }
    except Exception as e:
        logger.exception("[AUDITOR] error: %s", e)
        return {
            "subtasks": state["subtasks"],
            "status": "ERROR",
            "feedback_message": f"Auditor 오류: {e}",
        }


# Writer 노드: 최종 SubTask 리스트를 기반으로 SRS 문서를 생성
def writer_node(state: GraphState) -> GraphState:
    logger.info("[WRITER] start")
    chain = create_writer_chain()
    subtasks_json = json.dumps(state["subtasks"], ensure_ascii=False, indent=2)
    try:
        result = chain.invoke(
            {
                "parent_task_id": DEFAULT_TASK_ID,
                "subtasks_json": subtasks_json,
            }
        )
        logger.info("[WRITER] SRS 생성 완료 (길이=%d)", len(result.srs_document or ""))
        return {
            "subtasks": state["subtasks"],
            "status": "DONE",
            "feedback_message": "SRS 문서 생성 완료",
            "srs_document": result.srs_document,
        }
    except Exception as e:
        logger.exception("[WRITER] error: %s", e)
        return {
            "subtasks": state.get("subtasks", []),
            "status": "ERROR",
            "feedback_message": f"Writer 오류: {e}",
        }


MAX_REFINEMENT_ATTEMPTS = 10


# Auditor 결과를 보고 다음 노드(planner/writer/종료)를 결정
def decide_next_step(state: GraphState) -> str:
    logger.info(
        "[DECISION] status=%s retry=%s",
        state.get("status"),
        state.get("retry_count", 0),
    )
    status = state.get("status", "ERROR")
    retry = state.get("retry_count", 0)

    if status == "PASS":
        return "writer"

    if status == "REFINEMENT":
        if retry >= MAX_REFINEMENT_ATTEMPTS:
            logger.error("[DECISION] max retries exceeded")
            return END
        return "planner"

    if status == "ERROR":
        logger.error("[DECISION] ERROR 상태 — 종료")
        return END

    logger.warning("[DECISION] 알 수 없는 상태(%s) — 종료", status)
    return END


# LangGraph 워크플로우 정의
workflow = StateGraph(GraphState)
workflow.add_node("planner", planner_node)
workflow.add_node("auditor", auditor_node)
workflow.add_node("writer", writer_node)

workflow.set_entry_point("planner")
workflow.add_edge("planner", "auditor")
workflow.add_conditional_edges("auditor", decide_next_step)
workflow.add_edge("writer", END)

decomposition_app = workflow.compile()
