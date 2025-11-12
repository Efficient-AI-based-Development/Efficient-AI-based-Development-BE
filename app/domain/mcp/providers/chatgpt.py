"""fastMCP-backed providers for MCP runs."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx


class _BaseFastMCPProvider:
    """Execute MCP runs by delegating to fastMCP integrations."""

    def __init__(
        self,
        base_url: str,
        token: str,
        model: str,
        provider_key: str,
        timeout: float = 60.0,
    ) -> None:
        if not base_url:
            raise ValueError("fastMCP base URL이 설정되어 있지 않습니다.")
        if not token:
            raise ValueError("fastMCP 토큰이 설정되어 있지 않습니다.")

        self._base_url = base_url.rstrip("/")
        self._token = token
        self._model = model
        self._provider_key = provider_key
        self._timeout = timeout

    def run(self, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a ChatGPT completion with provided arguments."""
        arguments = arguments or {}

        model = arguments.get("model") or self._model
        prompt: Optional[str] = arguments.get("prompt") or arguments.get("input")
        messages = arguments.get("messages")
        temperature = arguments.get("temperature")
        max_tokens = arguments.get("maxTokens") or arguments.get("max_tokens")

        if messages and isinstance(messages, list):
            message_payload: List[Dict[str, Any]] = messages
        elif isinstance(prompt, str) and prompt.strip():
            message_payload = [{"role": "user", "content": prompt}]
        else:
            raise ValueError("ChatGPT 실행을 위해 prompt 또는 messages 인자가 필요합니다.")

        payload: Dict[str, Any] = {
            "provider": self._provider_key,
            "model": model,
            "messages": message_payload,
        }
        if temperature is not None:
            payload["temperature"] = float(temperature)
        if max_tokens is not None:
            payload["max_tokens"] = int(max_tokens)

        response = httpx.post(
            f"{self._base_url}/ai/chat",
            json=payload,
            headers={"Authorization": f"Bearer {self._token}"},
            timeout=self._timeout,
        )

        response.raise_for_status()
        data = response.json()

        if not data.get("ok", False):
            error = data.get("error") or {}
            raise ValueError(error.get("message") or "fastMCP ChatGPT 호출이 실패했습니다.")

        return {
            "output_text": data.get("text"),
            "model": data.get("model"),
            "usage": data.get("usage"),
            "raw": data,
        }


class ChatGPTProvider(_BaseFastMCPProvider):
    """fastMCP OpenAI provider."""

    def __init__(self, base_url: str, token: str, model: str, timeout: float = 60.0) -> None:
        super().__init__(
            base_url=base_url,
            token=token,
            model=model,
            provider_key="openai",
            timeout=timeout,
        )


class ClaudeProvider(_BaseFastMCPProvider):
    """fastMCP Anthropic provider."""

    def __init__(self, base_url: str, token: str, model: str, timeout: float = 60.0) -> None:
        super().__init__(
            base_url=base_url,
            token=token,
            model=model,
            provider_key="anthropic",
            timeout=timeout,
        )


