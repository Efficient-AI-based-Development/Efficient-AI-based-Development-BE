# ai_module/graphs/agents/auditor_agent.py

import json

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from ai_module.common.llm import get_llm, with_structured
from ai_module.common.prompts import auditor_system
from app.schemas.ai import AuditorOutput
from app.utils.logger import get_logger

logger = get_logger(__name__)


# Auditor LLM 체인 생성
def create_auditor_chain() -> Runnable:
    """
    SubTask JSON을 입력받아 PASS/REFINEMENT 결정을 내리는 Auditor 체인을 생성한다.
    """
    llm = with_structured(get_llm("auditor", temperature=0.0), AuditorOutput)
    system_prompt = auditor_system()
    schema_text = json.dumps(AuditorOutput.model_json_schema(), ensure_ascii=False, indent=2)

    human_prompt = "상위 Task: {parent_task_description}\nSubTask JSON: {subtasks_json}"

    prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", human_prompt)]).partial(
        schema_text=schema_text
    )
    return prompt | llm
