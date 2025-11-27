"""Configuration helpers for Efficient MCP CLI."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import json
import typer

CONFIG_DIR = Path.home() / ".efficient_mcp"
CONFIG_PATH = CONFIG_DIR / "config.json"


@dataclass
class Config:
    base_url: str
    project_id: str
    api_token: str | None = None
    connection_id: str | None = None
    session_id: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        return cls(
            base_url=data["base_url"],
            project_id=str(data["project_id"]),
            api_token=data.get("api_token"),
            connection_id=data.get("connection_id"),
            session_id=data.get("session_id"),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_config(required: bool = True) -> Config | None:
    if not CONFIG_PATH.exists():
        if required:
            typer.echo(
                "설정 파일이 없습니다. 먼저 `efficient-mcp configure` 명령을 실행해 주세요.",
                err=True,
            )
            raise typer.Exit(1)
        return None

    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return Config.from_dict(data)
    except Exception as exc:  # pragma: no cover - defensive
        typer.echo(f"설정 파일을 읽을 수 없습니다: {exc}", err=True)
        raise typer.Exit(1) from exc


def save_config(config: Config) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    typer.echo(f"설정이 저장되었습니다: {CONFIG_PATH}")



