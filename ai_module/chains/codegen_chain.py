# ai_module/chains/codegen_chain.py

from __future__ import annotations

import json

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from ai_module.common.llm import get_llm, with_structured
from ai_module.common.prompts import codegen_system
from app.schemas.ai import CodegenOutput, RepoSnapshot, SubTask


# CodegenOutput Pydantic 스키마를 LLM 프롬프트에 안전하게 넣기 위한 유틸
def _escape_json_for_template(d: dict) -> str:
    return json.dumps(d, ensure_ascii=False, indent=2).replace("{", "{{").replace("}", "}}")


# SubTask + RepoSnapshot을 입력으로 받아 CodegenOutput을 생성하는 LLM 체인 생성
def create_codegen_chain() -> Runnable:
    llm = with_structured(get_llm("codegen", temperature=0.25), CodegenOutput)

    schema_text = _escape_json_for_template(CodegenOutput.model_json_schema())
    system_prompt = codegen_system(schema_text)

    human_prompt = (
        "다음은 구현해야 할 SubTask와 현재 레포지토리 스냅샷입니다.\n\n"
        "=== SubTask JSON ===\n"
        "{subtask_json}\n\n"
        "=== RepoSnapshot JSON ===\n"
        "{repo_snapshot_json}\n\n"
        "위 정보를 바탕으로, 반드시 CodegenOutput 스키마에 맞는 JSON만 출력하세요."
    )

    prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", human_prompt)])
    return prompt | llm


# 단일 SubTask를 실제 CodegenOutput 결과로 변환하는 헬퍼 함수
def implement_subtask(subtask: SubTask, repo_snapshot: RepoSnapshot | None = None) -> CodegenOutput:
    chain = create_codegen_chain()

    subtask_json = subtask.model_dump_json(ensure_ascii=False, indent=2)

    if repo_snapshot:
        repo_snapshot_json = repo_snapshot.model_dump_json(ensure_ascii=False, indent=2)
    else:
        repo_snapshot_json = json.dumps(
            {"root": "", "branch": "", "commit": "", "files": []},
            ensure_ascii=False,
            indent=2,
        )

    result = chain.invoke(
        {
            "subtask_json": subtask_json,
            "repo_snapshot_json": repo_snapshot_json,
        }
    )

    if isinstance(result, CodegenOutput):
        return result

    if isinstance(result, dict):
        return CodegenOutput(**result)

    raise ValueError(f"Unexpected LLM result type for CodegenOutput: {type(result)}")


# SubTask, RepoSnapshot, 사용자 피드백을 기반으로 코드 변경 제안(CodegenOutput)을 생성하는 대화형 체인
def create_interactive_codegen_chain() -> Runnable:
    llm = with_structured(get_llm("codegen", temperature=0.25), CodegenOutput)

    schema_text = _escape_json_for_template(CodegenOutput.model_json_schema())
    system_prompt = codegen_system(schema_text)

    human_prompt = (
        "다음은 구현해야 할 SubTask와 현재 레포지토리 스냅샷, 그리고 사용자의 추가 요청입니다.\n\n"
        "=== SubTask JSON ===\n"
        "{subtask_json}\n\n"
        "=== RepoSnapshot JSON ===\n"
        "{repo_snapshot_json}\n\n"
        "=== 사용자 요청 ===\n"
        "{user_feedback}\n\n"
        "위 정보를 바탕으로, 반드시 CodegenOutput 스키마에 맞는 JSON만 출력하세요.\n"
        "또한, 변경된 코드와 함께 사용자 요청에 대한 친절한 안내 메시지를 message 필드에 한국어로 작성하세요."
    )

    prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", human_prompt)])
    return prompt | llm


# 단일 SubTask를 사용자 피드백과 함께 코드 변경 제안(CodegenOutput)으로 구현하는 함수
def implement_interactive_subtask(
    subtask: SubTask,
    repo_snapshot: RepoSnapshot | None = None,
    user_feedback: str = "",
) -> CodegenOutput:
    chain = create_interactive_codegen_chain()

    subtask_json = subtask.model_dump_json(ensure_ascii=False, indent=2)

    if repo_snapshot:
        repo_snapshot_json = repo_snapshot.model_dump_json(ensure_ascii=False, indent=2)
    else:
        repo_snapshot_json = json.dumps(
            {"root": "", "branch": "", "commit": "", "files": []},
            ensure_ascii=False,
            indent=2,
        )

    result = chain.invoke(
        {
            "subtask_json": subtask_json,
            "repo_snapshot_json": repo_snapshot_json,
            "user_feedback": user_feedback,
        }
    )

    if isinstance(result, CodegenOutput):
        return result

    if isinstance(result, dict):
        return CodegenOutput(**result)

    raise ValueError(f"Unexpected LLM result type for CodegenOutput: {type(result)}")
