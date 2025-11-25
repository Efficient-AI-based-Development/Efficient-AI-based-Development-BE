"""Efficient MCP CLI entrypoint."""

from __future__ import annotations

import json
import time
from typing import Any

import httpx
import typer

from .config import Config, load_config, save_config

app = typer.Typer(help="Efficient MCP CLI - 백엔드 MCP API를 명령행에서 실행합니다.")


def _build_client(config: Config) -> httpx.Client:
    headers = {}
    if config.api_token:
        headers["Authorization"] = f"Bearer {config.api_token}"

    base_url = config.base_url.rstrip("/")
    return httpx.Client(base_url=base_url, headers=headers, timeout=30.0)


def _ensure_connection(config: Config) -> str:
    if not config.connection_id:
        typer.echo("connection_id가 설정되어 있지 않습니다. `efficient-mcp connect --provider claude` 명령을 먼저 실행해 주세요.", err=True)
        raise typer.Exit(1)
    return config.connection_id


def _ensure_session(config: Config) -> str:
    if not config.session_id:
        typer.echo("session_id가 설정되어 있지 않습니다. `efficient-mcp create-session` 명령을 먼저 실행해 주세요.", err=True)
        raise typer.Exit(1)
    return config.session_id


@app.command("configure")
def configure(
    base_url: str = typer.Option(..., prompt=True, help="백엔드 API 기본 URL (예: http://localhost:8000)"),
    project_id: str = typer.Option(..., prompt=True, help="프로젝트 ID"),
    api_token: str = typer.Option(
        None,
        prompt="API 토큰이 있으면 입력하세요 (없으면 Enter)",
        hide_input=True,
        confirmation_prompt=False,
    ),
) -> None:
    """기본 설정을 저장합니다."""
    config = Config(base_url=base_url, project_id=project_id, api_token=api_token or None)
    save_config(config)


@app.command("show-config")
def show_config() -> None:
    """현재 설정을 출력합니다."""
    config = load_config()
    data = config.to_dict()
    masked = {**data, "api_token": "***" if data.get("api_token") else None}
    typer.echo(json.dumps(masked, indent=2, ensure_ascii=False))


@app.command("connect")
def create_connection(
    provider: str = typer.Option("claude", help="연결할 MCP provider ID (chatgpt / claude / cursor 중 선택)"),
) -> None:
    """새 MCP 연결을 생성하고 활성화합니다."""
    config = load_config()
    with _build_client(config) as client:
        payload = {"providerId": provider, "projectId": config.project_id}
        response = client.post("/api/v1/mcp/connections", json=payload)
        response.raise_for_status()
        connection_id = response.json()["data"]["connectionId"]

        typer.echo(f"연결 생성 완료: {connection_id}")
        activate = client.post(f"/api/v1/mcp/connections/{connection_id}/activate")
        activate.raise_for_status()
        typer.echo("연결이 active 상태로 전환되었습니다.")

    config.connection_id = connection_id
    save_config(config)


@app.command("create-session")
def create_session() -> None:
    """현재 연결로 MCP 세션을 생성합니다."""
    config = load_config()
    connection_id = _ensure_connection(config)
    
    with _build_client(config) as client:
        # 연결 상태 확인 및 필요시 활성화
        try:
            payload = {"connectionId": connection_id, "projectId": config.project_id}
            response = client.post("/api/v1/mcp/sessions", json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 400:
                error_data = exc.response.json()
                error_msg = error_data.get("error", "알 수 없는 오류")
                if "활성화된" in error_msg or "active" in error_msg.lower():
                    typer.echo("연결이 활성화되지 않았습니다. 연결을 활성화합니다...", err=True)
                    activate = client.post(f"/api/v1/mcp/connections/{connection_id}/activate")
                    activate.raise_for_status()
                    typer.echo("연결이 활성화되었습니다. 세션을 다시 생성합니다...")
                    # 재시도
                    response = client.post("/api/v1/mcp/sessions", json=payload)
                    response.raise_for_status()
                else:
                    typer.echo(f"세션 생성 실패: {error_msg}", err=True)
                    raise typer.Exit(1) from exc
            else:
                typer.echo(f"세션 생성 실패: HTTP {exc.response.status_code}", err=True)
                try:
                    error_data = exc.response.json()
                    typer.echo(f"오류 상세: {error_data}", err=True)
                except Exception:
                    typer.echo(f"응답: {exc.response.text}", err=True)
                raise typer.Exit(1) from exc
        
        session_id = response.json()["data"]["sessionId"]
        typer.echo(f"세션 생성 완료: {session_id}")

    config.session_id = session_id
    save_config(config)


@app.command("list-tools")
def list_tools() -> None:
    """사용 가능한 Tool 목록을 출력합니다."""
    config = load_config()
    session_id = _ensure_session(config)
    with _build_client(config) as client:
        response = client.get("/api/v1/mcp/tools", params={"sessionId": session_id})
        response.raise_for_status()
        tools = response.json()["data"]

    if not tools:
        typer.echo("사용 가능한 Tool이 없습니다.")
        return

    typer.echo("=== MCP Tools ===")
    for item in tools:
        typer.echo(f"- {item['toolId']}: {item.get('description', '')}")


def _parse_input(input_json: str | None) -> dict[str, Any]:
    if not input_json:
        return {}
    try:
        return json.loads(input_json)
    except json.JSONDecodeError as exc:
        typer.echo(f"input JSON 파싱 실패: {exc}", err=True)
        raise typer.Exit(1) from exc


@app.command("run-tool")
def run_tool(
    tool_id: str = typer.Option(..., "--tool-id", help="실행할 Tool ID"),
    input_json: str = typer.Option("{}", "--input", help='Tool 입력 JSON (예: \'{"args":{"foo":"bar"}}\')'),
    mode: str = typer.Option("tool", help="실행 모드 (기본: tool)"),
) -> None:
    """Tool을 실행하고 결과를 출력합니다."""
    config = load_config()
    session_id = _ensure_session(config)
    input_payload = _parse_input(input_json)

    with _build_client(config) as client:
        payload = {
            "sessionId": session_id,
            "mode": mode,
            "toolId": tool_id,
            "input": input_payload,
        }
        response = client.post("/api/v1/mcp/runs", json=payload)
        response.raise_for_status()
        data = response.json()["data"]
        run_id = data["runId"]
        typer.echo(f"실행 요청 완료. runId={run_id}")

        status = data["status"]
        status_data = data
        while status not in {"succeeded", "failed", "cancelled"}:
            time.sleep(0.5)
            status_resp = client.get(f"/api/v1/mcp/runs/{run_id}")
            status_resp.raise_for_status()
            status_data = status_resp.json()["data"]
            status = status_data["status"]

        typer.echo(f"실행 상태: {status}")
        if status == "failed":
            typer.echo(f"실행 실패: {status_data.get('message')}", err=True)
        result = status_data.get("result")
        if result:
            typer.echo("=== 결과 ===")
            typer.echo(json.dumps(result, indent=2, ensure_ascii=False))


@app.command("create-document")
def create_document(
    doc_type: str = typer.Option(..., "--type", help="문서 타입 (PRD, USER_STORY, SRS)"),
    title: str = typer.Option(..., "--title", help="문서 제목"),
    content_file: str = typer.Option(None, "--file", help="마크다운 파일 경로 (선택사항)"),
    content: str = typer.Option(None, "--content", help="문서 내용 (마크다운, 선택사항)"),
) -> None:
    """프로젝트에 문서를 생성합니다."""
    config = load_config()
    
    # 문서 타입 검증
    if doc_type not in {"PRD", "USER_STORY", "SRS"}:
        typer.echo(f"잘못된 문서 타입입니다. PRD, USER_STORY, SRS 중 하나를 선택하세요.", err=True)
        raise typer.Exit(1)
    
    # 내용 가져오기
    content_md = ""
    if content_file:
        from pathlib import Path
        file_path = Path(content_file)
        if not file_path.exists():
            typer.echo(f"파일을 찾을 수 없습니다: {content_file}", err=True)
            raise typer.Exit(1)
        content_md = file_path.read_text(encoding="utf-8")
    elif content:
        content_md = content
    else:
        # 기본 템플릿 제공
        if doc_type == "PRD":
            content_md = """# Product Requirements Document

## 개요
프로젝트에 대한 요구사항을 작성하세요.

## 목표
- 목표 1
- 목표 2

## 기능 요구사항
### 기능 1
- 설명

## 비기능 요구사항
- 성능
- 보안
- 확장성

## 제약사항
- 제약 1
"""
        elif doc_type == "USER_STORY":
            content_md = """# User Stories

## Story 1
As a [사용자 유형]
I want [원하는 기능]
So that [이유]

## Story 2
...
"""
        else:  # SRS
            content_md = """# Software Requirements Specification

## 시스템 개요
시스템에 대한 개요를 작성하세요.

## 기능 요구사항
### FR-1
- 설명

## 비기능 요구사항
### NFR-1
- 설명
"""
    
    # 프로젝트 ID를 정수로 변환
    try:
        project_id = int(config.project_id)
    except ValueError:
        typer.echo(f"프로젝트 ID가 올바르지 않습니다: {config.project_id}", err=True)
        raise typer.Exit(1)
    
    with _build_client(config) as client:
        payload = {
            "title": title,
            "type": doc_type,
            "content_md": content_md,
        }
        response = client.post(f"/api/v1/projects/{project_id}/", json=payload)
        response.raise_for_status()
        data = response.json()
        
        typer.echo(f"문서 생성 완료!")
        typer.echo(f"  ID: {data.get('id')}")
        typer.echo(f"  제목: {data.get('title')}")
        typer.echo(f"  타입: {data.get('type')}")


@app.command("status")
def status() -> None:
    """서버 상태를 간단히 점검합니다."""
    config = load_config()
    with _build_client(config) as client:
        response = client.get("/health")
        if response.status_code == 200:
            typer.echo("백엔드 서버 연결 성공.")
        else:
            typer.echo(f"백엔드 서버 응답 코드: {response.status_code}")

    typer.echo(f"현재 connectionId: {config.connection_id or '-'}")
    typer.echo(f"현재 sessionId: {config.session_id or '-'}")


if __name__ == "__main__":  # pragma: no cover
    app()


