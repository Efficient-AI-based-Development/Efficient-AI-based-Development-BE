# ai_module/chains/tasklist_chain.py

from __future__ import annotations

import json

from langchain_core.prompts import ChatPromptTemplate

from ai_module.common.llm import get_llm, with_structured
from ai_module.common.prompts import tasklist_system
from app.schemas.ai import TaskListOutput


# Task List 생성을 위한 LLM 체인 구성
def create_tasklist_generation_chain():
    llm = with_structured(get_llm("tasklist", temperature=0.3), TaskListOutput)
    system_prompt = tasklist_system()

    human_prompt = "=== PRD (선택) ===\n{prd_document}\n\n" "=== 추가 설명 (선택) ===\n{user_input}\n"

    prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", human_prompt)])

    schema_text = json.dumps(
        TaskListOutput.model_json_schema(),
        ensure_ascii=False,
        indent=2,
    )
    return prompt | llm, schema_text


# TaskListOutput 생성
def generate_tasklist(prd_document: str | None, user_input: str | None) -> TaskListOutput:
    chain, schema_text = create_tasklist_generation_chain()
    result = chain.invoke(
        {
            "prd_document": prd_document or "",
            "user_input": user_input or "",
            "schema_text": schema_text,
        }
    )

    if isinstance(result, TaskListOutput):
        return result
    if isinstance(result, dict):
        return TaskListOutput(**result)
    return TaskListOutput(project_name="[ERROR] 생성 실패", tasks=[])
