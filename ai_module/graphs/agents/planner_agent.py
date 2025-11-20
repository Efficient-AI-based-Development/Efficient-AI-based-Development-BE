# ai_module/graphs/agents/planner_agent.py

import json

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from ai_module.common.llm import get_llm, with_structured
from ai_module.common.prompts import planner_system
from app.schemas.ai import PlannerOutput


# Planner LLM 체인 생성
def create_planner_chain() -> Runnable:
    """
    상위 Task ID/설명/피드백을 입력받아 PlannerOutput(SubTask 리스트)을 생성하는 체인.
    """
    llm = with_structured(get_llm("planner", temperature=0.3), PlannerOutput)
    system_prompt = planner_system()
    schema_text = json.dumps(PlannerOutput.model_json_schema(), ensure_ascii=False, indent=2)

    human_prompt = "Task ID: {parent_task_id}\n설명: {task_description}\n피드백: {feedback}"

    prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", human_prompt)]).partial(
        schema_text=schema_text
    )
    return prompt | llm
