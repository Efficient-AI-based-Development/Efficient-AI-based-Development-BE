"""Simple fastMCP CLI used in guides to mimic vooster.ai experience."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import httpx
import typer

app = typer.Typer(help="fastMCP CLI helper")

CONFIG_DIR = Path.home() / ".fastmcp"
CONFIG_FILE = CONFIG_DIR / "config.json"
PROJECT_DIR = Path(".fastmcp")
PROJECT_FILE = PROJECT_DIR / "project.json"

PROVIDER_MAP = {
    "chatgpt": ("openai", "gpt-4o-mini"),
    "claude": ("anthropic", "claude-3-sonnet"),
}


def save_config(data: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        typer.secho("로그인이 필요합니다. 먼저 `fastmcp login`을 실행하세요.", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))


def save_project(data: dict) -> None:
    PROJECT_DIR.mkdir(parents=True, exist_ok=True)
    PROJECT_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_project() -> dict:
    if PROJECT_FILE.exists():
        return json.loads(PROJECT_FILE.read_text(encoding="utf-8"))
    return {}


@app.command()
def login(
    token: str = typer.Option(..., prompt=True, hide_input=True, help="fastMCP 토큰"),
    base_url: str = typer.Option(
        "http://localhost:8787",
        "--base-url",
        help="fastMCP 서버 주소 (기본: http://localhost:8787)",
    ),
) -> None:
    """fastMCP 서버 인증 정보를 저장합니다."""
    config = {"base_url": base_url.rstrip("/"), "token": token}
    save_config(config)
    typer.secho("fastMCP 인증 정보가 저장되었습니다.", fg=typer.colors.GREEN)


@app.command()
def init(
    project: Optional[str] = typer.Option(
        None,
        "--project",
        "-p",
        help="프로젝트 식별자. 지정하지 않으면 프롬프트로 입력받습니다.",
    ),
    provider: str = typer.Option(
        "chatgpt",
        "--provider",
        "-r",
        help="사용할 MCP 제공자 (기본: chatgpt)",
    ),
) -> None:
    """현재 작업 디렉터리에 fastMCP 프로젝트 설정을 생성합니다."""
    if project is None:
        project = typer.prompt("프로젝트 ID를 입력하세요", default="demo-project")
    provider = provider.lower()
    provider_key, default_model = PROVIDER_MAP.get(provider, (provider, "gpt-4o-mini"))
    data = {"project": project, "provider": provider, "provider_key": provider_key, "model": default_model}
    save_project(data)
    typer.secho(
        f".fastmcp/project.json 파일이 생성되었습니다. (project={project}, provider={provider}, model={default_model})",
        fg=typer.colors.GREEN,
    )


@app.command()
def status() -> None:
    """fastMCP 서버 상태를 점검합니다."""
    config = load_config()
    try:
        resp = httpx.get(
            f"{config['base_url']}/health",
            headers={"Authorization": f"Bearer {config['token']}"},
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()
        typer.echo(f"fastMCP 서버 연결 성공: mode={data.get('mode')}")
    except Exception as exc:  # pylint: disable=broad-except
        typer.secho(f"fastMCP 서버 연결 실패: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc


@app.command()
def run(
    prompt: str = typer.Option(
        "이번 sprint 요약해줘",
        "--prompt",
        "-m",
        help="실행할 사용자 프롬프트",
    ),
) -> None:
    """fastMCP 서버를 통해 AI 채팅을 실행합니다."""
    config = load_config()
    project = load_project()
    provider = project.get("provider", "chatgpt")
    if provider in PROVIDER_MAP:
        provider_key, default_model = PROVIDER_MAP[provider]
    else:
        provider_key = project.get("provider_key", provider)
        default_model = project.get("model", "gpt-4o-mini")

    payload = {
        "provider": provider_key,
        "model": project.get("model", default_model),
        "messages": [
            {"role": "system", "content": "You are an assistant helping developers."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 400,
    }

    typer.echo("fastMCP 서버로 요청을 전송 중입니다...")
    try:
        resp = httpx.post(
            f"{config['base_url']}/ai/chat",
            headers={"Authorization": f"Bearer {config['token']}"},
            json=payload,
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # pylint: disable=broad-except
        typer.secho(f"요청 실패: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    if not data.get("ok", False):
        typer.secho(f"fastMCP 오류: {data.get('error')}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    typer.secho("=== fastMCP 응답 ===", fg=typer.colors.GREEN)
    typer.echo(data.get("text") or data)


if __name__ == "__main__":
    app()

