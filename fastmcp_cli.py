"""Simple fastMCP CLI used in guides to mimic vooster.ai experience."""

from __future__ import annotations

import json
from pathlib import Path

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
    "cursor": ("openai", "gpt-4o-mini"),  # Cursor는 OpenAI 기반
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
    project: str | None = typer.Option(
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


def _build_system_prompt(project_id: str | None = None) -> str:
    """프로젝트 컨텍스트를 포함한 시스템 프롬프트 생성."""
    base_prompt = "You are an assistant helping developers with their projects."
    if project_id:
        base_prompt += f" The current project ID is {project_id}."
    return base_prompt


@app.command()
def run(
    prompt: str | None = typer.Argument(
        None,
        help="실행할 사용자 프롬프트 또는 자연어 명령어 (예: '프로젝트 JYVP의 다음 작업 진행')",
    ),
    project_id: str | None = typer.Option(
        None,
        "--project",
        "-p",
        help="프로젝트 ID (자연어 명령어에 포함되어 있으면 생략 가능)",
    ),
) -> None:
    """fastMCP 서버를 통해 AI 채팅을 실행합니다.
    
    자연어 명령어와 직접 프롬프트를 모두 지원합니다.
    
    예시:
        # 직접 프롬프트
        fastmcp run "이번 sprint 요약해줘"
        
        # 자연어 명령어 (vooster.ai 스타일)
        fastmcp run "프로젝트 JYVP의 다음 작업 진행"
        fastmcp run "프로젝트 JYVP의 T-001 작업 수행"
        
        # 프로젝트 ID 명시
        fastmcp run "다음 작업 진행" --project JYVP
    """
    config = load_config()
    project = load_project()

    # 프로젝트 ID 우선순위: 명령어 옵션 > 프로젝트 파일 > 자연어에서 추출
    resolved_project_id = project_id or project.get("project")

    # 프롬프트가 없으면 대화형으로 입력받기
    if prompt is None:
        prompt = typer.prompt("프롬프트를 입력하세요", default="이번 sprint 요약해줘")

    provider = project.get("provider", "chatgpt")
    if provider in PROVIDER_MAP:
        provider_key, default_model = PROVIDER_MAP[provider]
    else:
        provider_key = project.get("provider_key", provider)
        default_model = project.get("model", "gpt-4o-mini")

    # 시스템 프롬프트에 프로젝트 컨텍스트 추가
    system_content = _build_system_prompt(resolved_project_id)

    # 자연어 명령어를 더 명확하게 처리하기 위한 컨텍스트 추가
    user_content = prompt
    if resolved_project_id and "프로젝트" in prompt and resolved_project_id not in prompt:
        # 자연어에 프로젝트 ID가 없으면 추가
        user_content = f"프로젝트 {resolved_project_id}의 {prompt}"

    payload = {
        "provider": provider_key,
        "model": project.get("model", default_model),
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.2,
        "max_tokens": 2000,  # 더 긴 응답을 위해 증가
    }

    typer.echo(f"fastMCP 서버로 요청을 전송 중입니다... (프로젝트: {resolved_project_id or '미지정'})")
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

