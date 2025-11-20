# ai_module/common/ids.py

from __future__ import annotations

from typing import Any


#
def normalize_ids(payload: Any) -> Any:
    """
    DecompositionOutput 형태의 dict에 대해
    각 SubTask에 ST-<task_id>-NN 형식의 일관된 ID를 부여하고
    dependencies 안의 참조도 새 ID로 치환한다.

    - payload 가 dict 이 아닌 경우(그냥 Pydantic 모델 등)는 그대로 반환한다.
    - 반환값은 { "items": ..., "all_subtasks": ... } 구조의 dict 이다.
    """
    if not isinstance(payload, dict):
        return payload

    items: list[dict[str, Any]] = payload.get("items", [])
    all_subtasks: list[dict[str, Any]] = payload.get("all_subtasks", [])

    id_map: dict[str, str] = {}

    # items 내부 subtasks에 새 ID 부여
    for item in items:
        tid = item["task_id"]
        seq = 1
        for st in item.get("subtasks", []):
            old_id = st.get("subtask_id", "")
            new_id = f"ST-{tid}-{seq:02d}"
            id_map[old_id] = new_id
            st["subtask_id"] = new_id
            st["dependencies"] = [id_map.get(d, d) for d in st.get("dependencies", [])]
            seq += 1

    # all_subtasks 에도 동일한 규칙 적용
    for st in all_subtasks:
        old_id = st.get("subtask_id", "")
        if old_id in id_map:
            st["subtask_id"] = id_map[old_id]
        st["dependencies"] = [id_map.get(d, d) for d in st.get("dependencies", [])]

    return {"items": items, "all_subtasks": all_subtasks}
