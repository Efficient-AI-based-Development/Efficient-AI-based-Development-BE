# server.py
import os
from typing import List, Optional, Literal

import anthropic
from fastapi import FastAPI, Header, HTTPException
from openai import OpenAI
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

FASTMCP_TOKEN = os.getenv("FASTMCP_TOKEN")
MODE = os.getenv("FASTMCP_MODE", "mock")  # mock | real
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

openai_client: Optional[OpenAI] = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
anthropic_client: Optional[anthropic.Anthropic] = (
    anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None
)

app = FastAPI(title="fastmcp (FastAPI)")

class Msg(BaseModel):
    role: Literal["user","assistant","system"]
    content: str

class ChatReq(BaseModel):
    provider: Literal["openai","anthropic"]
    model: str
    messages: List[Msg]
    max_tokens: Optional[int] = 1024
    temperature: Optional[float] = 0.2

def assert_authz(auth: Optional[str]):
    if not FASTMCP_TOKEN:
        # 서버 설정 문제는 500으로
        raise HTTPException(500, "Server missing FASTMCP_TOKEN")
    if auth != f"Bearer {FASTMCP_TOKEN}":
        raise HTTPException(401, "Invalid or missing fastmcp token")

@app.get("/health")
def health():
    return {"ok": True, "mode": MODE}

@app.post("/ai/chat")
def ai_chat(body: ChatReq, authorization: Optional[str] = Header(None)):
    assert_authz(authorization)

    # 1) 모의(mock) 모드: 외부 API 호출 없이 성공 응답
    if MODE == "mock":
        user_text = next((m.content for m in body.messages if m.role == "user"), "")
        return {
            "ok": True,
            "provider": body.provider,
            "model": body.model,
            "text": f"[MOCK] {user_text[:100]}",
            "usage": {"input": len(user_text), "output": len(user_text[:100])},
        }

    # 2) real 모드 호출
    if MODE != "real":
        raise HTTPException(400, "FASTMCP_MODE=real 로 설정되어 있지 않습니다.")

    if body.provider == "openai":
        if not openai_client:
            raise HTTPException(500, "OPENAI_API_KEY가 설정되어 있지 않습니다.")
        response = openai_client.responses.create(
            model=body.model,
            messages=[m.model_dump() for m in body.messages],
            max_output_tokens=body.max_tokens,
            temperature=body.temperature,
        )
        data = response.model_dump(mode="json")
        return {
            "ok": True,
            "provider": body.provider,
            "model": body.model,
            "text": getattr(response, "output_text", None),
            "usage": data.get("usage"),
            "raw": data,
        }

    if body.provider == "anthropic":
        if not anthropic_client:
            raise HTTPException(500, "ANTHROPIC_API_KEY가 설정되어 있지 않습니다.")

        system_prompt = "\n".join(
            m.content for m in body.messages if m.role == "system" and m.content
        ) or None
        messages_payload = [
            {"role": m.role, "content": m.content}
            for m in body.messages
            if m.role != "system"
        ]
        response = anthropic_client.messages.create(
            model=body.model,
            max_output_tokens=body.max_tokens or 1024,
            temperature=body.temperature or 0.2,
            system=system_prompt,
            messages=[{"role": m["role"], "content": [{"type": "text", "text": m["content"]}]} for m in messages_payload],
        )
        text = ""
        if response.content:
            text = " ".join(
                block.text for block in response.content if hasattr(block, "text")
            )
        data = response.model_dump(mode="json")
        return {
            "ok": True,
            "provider": body.provider,
            "model": body.model,
            "text": text,
            "usage": data.get("usage"),
            "raw": data,
        }

    raise HTTPException(400, f"지원하지 않는 provider: {body.provider}")