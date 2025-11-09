"""ChatGPT provider implementation for MCP runs."""

from __future__ import annotations

from typing import Any, Dict, Optional

from openai import OpenAI


class ChatGPTProvider:
    """Execute MCP runs using OpenAI's ChatGPT models."""

    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise ValueError("OpenAI API 키가 설정되어 있지 않습니다.")
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def run(self, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a ChatGPT completion with provided arguments."""
        arguments = arguments or {}

        model = arguments.get("model") or self._model
        prompt: Optional[str] = arguments.get("prompt") or arguments.get("input")
        messages = arguments.get("messages")
        temperature = arguments.get("temperature")
        max_tokens = arguments.get("maxTokens") or arguments.get("max_tokens")

        if messages and isinstance(messages, list):
            input_payload: Any = messages
        elif isinstance(prompt, str) and prompt.strip():
            input_payload = prompt
        else:
            raise ValueError("ChatGPT 실행을 위해 prompt 또는 messages 인자가 필요합니다.")

        request_kwargs: Dict[str, Any] = {
            "model": model,
            "input": input_payload,
        }
        if temperature is not None:
            request_kwargs["temperature"] = float(temperature)
        if max_tokens is not None:
            request_kwargs["max_output_tokens"] = int(max_tokens)

        response = self._client.responses.create(**request_kwargs)

        raw_payload: Optional[Dict[str, Any]] = None
        if hasattr(response, "model_dump"):
            raw_payload = response.model_dump(mode="json")  # type: ignore[assignment]

        return {
            "output_text": getattr(response, "output_text", None),
            "model": getattr(response, "model", None),
            "usage": raw_payload.get("usage") if isinstance(raw_payload, dict) else None,
            "raw": raw_payload,
        }


