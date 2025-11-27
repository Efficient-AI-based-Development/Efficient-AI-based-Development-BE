"""MCP Adapter Server for Claude Desktop.

백엔드 REST API를 MCP 프로토콜로 변환하여 Claude Desktop과 연동합니다.
"""

import asyncio
import json
import os
import sys
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    ListPromptsRequest,
    ListResourcesRequest,
    ListToolsRequest,
    ReadResourceRequest,
    TextContent,
    Tool,
)

# 환경 변수에서 설정 읽기
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
API_TOKEN = os.getenv("API_TOKEN", "")
PROJECT_ID = os.getenv("PROJECT_ID", "")
CONNECTION_ID = os.getenv("CONNECTION_ID", "")
SESSION_ID = os.getenv("SESSION_ID", "")

# MCP 서버 생성
app = Server("atlas-ai-mcp")

# HTTP 클라이언트
# MCP API는 인증이 필요 없을 수 있음 (실제 확인 필요)
client = httpx.AsyncClient(
    base_url=BACKEND_URL,
    headers={"Authorization": f"Bearer {API_TOKEN}"} if API_TOKEN else {},
    timeout=30.0,
)


async def ensure_session() -> str:
    """세션이 없으면 생성하고 반환."""
    global SESSION_ID

    if SESSION_ID:
        return SESSION_ID

    if not CONNECTION_ID:
        raise ValueError("CONNECTION_ID 환경 변수가 설정되지 않았습니다.")

    if not PROJECT_ID:
        raise ValueError("PROJECT_ID 환경 변수가 설정되지 않았습니다.")

    # 세션 생성
    try:
        response = await client.post(
            "/api/v1/mcp/sessions",
            json={
                "connectionId": CONNECTION_ID,
                "projectId": PROJECT_ID,
            },
        )
        response.raise_for_status()
        data = response.json()["data"]
        SESSION_ID = data["sessionId"]
        print(f"Session created: {SESSION_ID}", file=sys.stderr)
        return SESSION_ID
    except httpx.HTTPStatusError as e:
        error_msg = f"세션 생성 실패 (HTTP {e.response.status_code}): {e.response.text}"
        print(error_msg, file=sys.stderr)
        raise RuntimeError(error_msg) from e
    except Exception as e:
        error_msg = f"세션 생성 오류: {str(e)}"
        print(error_msg, file=sys.stderr)
        raise


@app.list_tools()
async def list_tools() -> list[Tool]:
    """사용 가능한 tool 목록 반환."""
    try:
        session_id = await ensure_session()
        response = await client.get(
            "/api/v1/mcp/tools",
            params={"sessionId": session_id},
        )
        response.raise_for_status()
        tools_data = response.json()["data"]

        # MCP Tool 형식으로 변환
        tools = []
        for tool_data in tools_data:
            tools.append(
                Tool(
                    name=tool_data["toolId"],
                    description=tool_data.get("description", ""),
                    inputSchema=tool_data.get("inputSchema", {}),
                )
            )
        return tools
    except httpx.HTTPStatusError as e:
        print(
            f"Error listing tools (HTTP {e.response.status_code}): {e.response.text}",
            file=sys.stderr,
        )
        return []
    except Exception as e:
        print(f"Error listing tools: {e}", file=sys.stderr)
        return []


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Tool 실행."""
    try:
        session_id = await ensure_session()

        # 백엔드 API 호출
        response = await client.post(
            "/api/v1/mcp/runs",
            json={
                "sessionId": session_id,
                "mode": "tool",
                "toolId": name,
                "input": arguments,
            },
        )
        response.raise_for_status()
        run_data = response.json()["data"]

        # 실행 상태 확인
        run_id = run_data["runId"]
        max_attempts = 10
        for _ in range(max_attempts):
            status_response = await client.get(f"/api/v1/mcp/runs/{run_id}")
            status_response.raise_for_status()
            status_data = status_response.json()["data"]

            if status_data["status"] in ["succeeded", "failed", "cancelled"]:
                result = status_data.get("result", {})
                
                # result가 문자열인 경우 JSON 파싱 시도
                if isinstance(result, str):
                    try:
                        result = json.loads(result)
                    except (json.JSONDecodeError, TypeError):
                        pass
                
                if status_data["status"] == "failed":
                    # MCP SDK 형식: TextContent 리스트
                    error_msg = result.get("error", status_data.get('message', 'Unknown error')) if isinstance(result, dict) else str(result)
                    return [
                        TextContent(
                            type="text",
                            text=f"❌ Tool 실행 실패: {error_msg}",
                        )
                    ]
                
                # 성공 시: result를 읽기 쉬운 형식으로 변환
                if isinstance(result, dict):
                    # generate_code 툴의 경우 특별 처리
                    if name == "generate_code" and "code" in result:
                        # 프롬프트를 직접 포함하여 Cursor가 바로 사용할 수 있도록
                        code_content = result.get('code', '')
                        summary = result.get('summary', 'N/A')
                        task_title = result.get('collectedContext', {}).get('taskTitle', 'N/A')
                        
                        # 명확하고 강조된 형식으로 변환
                        # 프롬프트 내용을 직접 사용 (이미 태스크 정보가 포함되어 있음)
                        formatted_text = f"""✅ 태스크 정보 수집 완료

{summary}

---

## ⚠️ 중요: 아래 프롬프트를 정확히 따라 구현하세요

프롬프트에 포함된 태스크 요구사항을 정확히 구현해야 합니다.
다른 태스크나 일반적인 코드를 생성하지 마세요.

---

{code_content}

---

## 📁 추가 정보
- 파일 경로: {result.get('filePath', '미지정')}
- 메시지: {result.get('message', 'N/A')}

**위 프롬프트의 태스크 요구사항을 정확히 따라 구현하세요.**
"""
                    elif name == "start_development":
                        # start_development 툴의 경우
                        formatted_text = f"""✅ 개발 시작 완료

{json.dumps(result, indent=2, ensure_ascii=False)}
"""
                    else:
                        # 다른 툴의 경우 JSON 형식으로
                        formatted_text = json.dumps(result, indent=2, ensure_ascii=False)
                else:
                    formatted_text = str(result)
                
                return [
                    TextContent(
                        type="text",
                        text=formatted_text,
                    )
                ]

            await asyncio.sleep(0.5)

        # 시간 초과
        return [
            TextContent(
                type="text",
                text="Tool 실행 시간 초과",
            )
        ]
    except Exception as e:
        error_msg = str(e)
        if isinstance(e, httpx.HTTPStatusError):
            error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
        print(f"Tool execution error: {error_msg}", file=sys.stderr)
        return [
            TextContent(
                type="text",
                text=f"Tool 실행 오류: {error_msg}",
            )
        ]


@app.list_resources()
async def list_resources() -> list[dict[str, Any]]:
    """사용 가능한 resource 목록 반환."""
    try:
        session_id = await ensure_session()
        response = await client.get(
            "/api/v1/mcp/resources",
            params={"sessionId": session_id},
        )
        response.raise_for_status()
        resources_data = response.json()["data"]

        # MCP Resource 형식으로 변환
        resources = []
        for resource_data in resources_data:
            resources.append(
                {
                    "uri": resource_data["uri"],
                    "name": resource_data.get("description", resource_data["uri"]),
                    "description": resource_data.get("description", ""),
                    "mimeType": "text/plain",
                }
            )
        return resources
    except httpx.HTTPStatusError as e:
        print(
            f"Error listing resources (HTTP {e.response.status_code}): {e.response.text}",
            file=sys.stderr,
        )
        return []
    except Exception as e:
        print(f"Error listing resources: {e}", file=sys.stderr)
        return []


@app.read_resource()
async def read_resource(uri: str) -> str:
    """Resource 읽기."""
    try:
        session_id = await ensure_session()
        response = await client.get(
            "/api/v1/mcp/resources/read",
            params={"sessionId": session_id, "uri": uri},
        )
        response.raise_for_status()
        data = response.json()["data"]

        # JSON을 문자열로 변환
        return json.dumps(data, ensure_ascii=False, indent=2)
    except httpx.HTTPStatusError as e:
        error_msg = f"Resource 읽기 HTTP 오류 ({e.response.status_code}): {e.response.text}"
        print(error_msg, file=sys.stderr)
        return error_msg
    except Exception as e:
        error_msg = f"Resource 읽기 오류: {str(e)}"
        print(error_msg, file=sys.stderr)
        return error_msg


@app.list_prompts()
async def list_prompts() -> list[dict[str, Any]]:
    """사용 가능한 prompt 목록 반환."""
    try:
        session_id = await ensure_session()
        response = await client.get(
            "/api/v1/mcp/prompts",
            params={"sessionId": session_id},
        )
        response.raise_for_status()
        prompts_data = response.json()["data"]

        # MCP Prompt 형식으로 변환
        prompts = []
        for prompt_data in prompts_data:
            prompts.append(
                {
                    "name": prompt_data["promptId"],
                    "description": prompt_data.get("description", ""),
                }
            )
        return prompts
    except httpx.HTTPStatusError as e:
        print(
            f"Error listing prompts (HTTP {e.response.status_code}): {e.response.text}",
            file=sys.stderr,
        )
        return []
    except Exception as e:
        print(f"Error listing prompts: {e}", file=sys.stderr)
        return []


async def main():
    """MCP 서버 실행."""
    # 필수 환경 변수 확인
    if not BACKEND_URL:
        print("ERROR: BACKEND_URL 환경 변수가 설정되지 않았습니다.", file=sys.stderr)
        sys.exit(1)

    if not PROJECT_ID:
        print("ERROR: PROJECT_ID 환경 변수가 설정되지 않았습니다.", file=sys.stderr)
        sys.exit(1)

    if not CONNECTION_ID:
        print("ERROR: CONNECTION_ID 환경 변수가 설정되지 않았습니다.", file=sys.stderr)
        sys.exit(1)

    # stdio 서버 실행 (app은 stdio_server가 아닌 app.run에 전달)
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())

