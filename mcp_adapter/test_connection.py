"""MCP 어댑터 서버 연결 테스트 스크립트.

백엔드 API와의 연결을 테스트하고 환경 설정을 검증합니다.
"""

import asyncio
import os
import sys
from typing import Any

import httpx


async def test_backend_connection(base_url: str) -> bool:
    """백엔드 서버 연결 테스트."""
    try:
        async with httpx.AsyncClient(base_url=base_url, timeout=5.0) as client:
            # Health check 또는 docs 엔드포인트 확인
            response = await client.get("/docs")
            if response.status_code == 200:
                print(f"✅ 백엔드 서버 연결 성공: {base_url}")
                return True
            else:
                print(f"❌ 백엔드 서버 응답 오류: {response.status_code}")
                return False
    except httpx.ConnectError:
        print(f"❌ 백엔드 서버에 연결할 수 없습니다: {base_url}")
        print("   백엔드 서버가 실행 중인지 확인하세요.")
        return False
    except Exception as e:
        print(f"❌ 연결 테스트 실패: {e}")
        return False


async def test_mcp_api(
    base_url: str, session_id: str, api_token: str = ""
) -> bool:
    """MCP API 엔드포인트 테스트."""
    headers = {}
    if api_token:
        headers["Authorization"] = f"Bearer {api_token}"

    try:
        async with httpx.AsyncClient(
            base_url=base_url, headers=headers, timeout=10.0
        ) as client:
            # Tools API 테스트
            response = await client.get(
                "/api/v1/mcp/tools", params={"sessionId": session_id}
            )
            if response.status_code == 200:
                print(f"✅ MCP Tools API 테스트 성공")
                data = response.json()
                tools = data.get("data", [])
                print(f"   사용 가능한 Tool 수: {len(tools)}")
                return True
            else:
                print(f"❌ MCP Tools API 오류: {response.status_code}")
                print(f"   응답: {response.text}")
                return False
    except Exception as e:
        print(f"❌ MCP API 테스트 실패: {e}")
        return False


async def create_test_session(
    base_url: str, connection_id: str, project_id: str, api_token: str = ""
) -> str | None:
    """테스트용 세션 생성."""
    headers = {"Content-Type": "application/json"}
    if api_token:
        headers["Authorization"] = f"Bearer {api_token}"

    try:
        async with httpx.AsyncClient(
            base_url=base_url, headers=headers, timeout=10.0
        ) as client:
            response = await client.post(
                "/api/v1/mcp/sessions",
                json={"connectionId": connection_id, "projectId": project_id},
            )
            if response.status_code == 201:
                data = response.json()["data"]
                session_id = data["sessionId"]
                print(f"✅ 테스트 세션 생성 성공: {session_id}")
                return session_id
            else:
                print(f"❌ 세션 생성 실패: {response.status_code}")
                print(f"   응답: {response.text}")
                return None
    except Exception as e:
        print(f"❌ 세션 생성 오류: {e}")
        return None


def check_environment() -> dict[str, str]:
    """환경 변수 확인."""
    env_vars = {
        "BACKEND_URL": os.getenv("BACKEND_URL", ""),
        "PROJECT_ID": os.getenv("PROJECT_ID", ""),
        "CONNECTION_ID": os.getenv("CONNECTION_ID", ""),
        "SESSION_ID": os.getenv("SESSION_ID", ""),
        "API_TOKEN": os.getenv("API_TOKEN", ""),
    }

    print("\n=== 환경 변수 확인 ===")
    for key, value in env_vars.items():
        if value:
            # API_TOKEN은 일부만 표시
            if key == "API_TOKEN":
                display_value = f"{value[:10]}..." if len(value) > 10 else "***"
            else:
                display_value = value
            print(f"✅ {key}: {display_value}")
        else:
            print(f"⚠️  {key}: 설정되지 않음")

    return env_vars


async def main():
    """메인 테스트 함수."""
    print("=" * 50)
    print("MCP 어댑터 서버 연결 테스트")
    print("=" * 50)

    # 환경 변수 확인
    env_vars = check_environment()

    # 필수 환경 변수 확인
    if not env_vars["BACKEND_URL"]:
        print("\n❌ BACKEND_URL이 설정되지 않았습니다.")
        sys.exit(1)

    if not env_vars["PROJECT_ID"]:
        print("\n❌ PROJECT_ID가 설정되지 않았습니다.")
        sys.exit(1)

    # 백엔드 연결 테스트
    print("\n=== 백엔드 서버 연결 테스트 ===")
    backend_ok = await test_backend_connection(env_vars["BACKEND_URL"])

    if not backend_ok:
        print("\n❌ 백엔드 서버 연결 실패. 테스트를 중단합니다.")
        sys.exit(1)

    # 세션 확인/생성
    session_id = env_vars["SESSION_ID"]
    if not session_id and env_vars["CONNECTION_ID"]:
        print("\n=== 테스트 세션 생성 ===")
        session_id = await create_test_session(
            env_vars["BACKEND_URL"],
            env_vars["CONNECTION_ID"],
            env_vars["PROJECT_ID"],
            env_vars["API_TOKEN"],
        )

    if not session_id:
        print("\n⚠️  SESSION_ID가 없어 MCP API 테스트를 건너뜁니다.")
        print("   CONNECTION_ID를 설정하고 연결을 활성화한 후 다시 시도하세요.")
        sys.exit(0)

    # MCP API 테스트
    print("\n=== MCP API 테스트 ===")
    api_ok = await test_mcp_api(
        env_vars["BACKEND_URL"], session_id, env_vars["API_TOKEN"]
    )

    # 결과 요약
    print("\n" + "=" * 50)
    print("테스트 결과 요약")
    print("=" * 50)
    print(f"백엔드 연결: {'✅ 성공' if backend_ok else '❌ 실패'}")
    print(f"MCP API: {'✅ 성공' if api_ok else '❌ 실패'}")

    if backend_ok and api_ok:
        print("\n✅ 모든 테스트 통과! MCP 어댑터 서버를 실행할 수 있습니다.")
        print(f"\n다음 명령으로 실행하세요:")
        print(f"  uv run python mcp_adapter/server.py")
    else:
        print("\n❌ 일부 테스트 실패. 위의 오류 메시지를 확인하세요.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

