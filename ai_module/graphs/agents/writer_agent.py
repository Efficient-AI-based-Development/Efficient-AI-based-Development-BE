# ai_module/graphs/agents/writer_agent.py

import json

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from ai_module.common.llm import get_llm, with_structured
from ai_module.common.prompts import writer_system
from app.schemas.ai import WriterOutput


# Writer LLM 체인 생성
def create_writer_chain() -> Runnable:
    llm = with_structured(get_llm("writer", temperature=0.4), WriterOutput)
    system_prompt = writer_system()
    schema_text = json.dumps(WriterOutput.model_json_schema(), ensure_ascii=False, indent=2)

    human_prompt = "Task ID: {parent_task_id}\nSubTask JSON: {subtasks_json}"

    prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", human_prompt)]).partial(
        schema_text=schema_text
    )
    return prompt | llm
