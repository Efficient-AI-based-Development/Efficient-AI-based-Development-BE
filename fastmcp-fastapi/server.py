# server.py
import os
from typing import List, Optional, Literal
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

FASTMCP_TOKEN = os.getenv("FASTMCP_TOKEN")
MODE = os.getenv("FASTMCP_MODE", "mock")  # mock | real

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

    # 2) real 모드인데 아직 미구현이면 501로 명시
    return {
        "ok": False,
        "error": {
            "type": "NotImplemented",
            "message": "Upstream provider call not implemented yet (openai/anthropic).",
        },
    }