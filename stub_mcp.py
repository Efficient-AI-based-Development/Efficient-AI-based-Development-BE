from fastapi import FastAPI
from pydantic import BaseModel
app = FastAPI()

class ChatRequest(BaseModel):
    provider: str
    model: str | None = None
    messages: list

@app.post("/ai/chat")
def chat(req: ChatRequest):
    # 실제 응답 대신 테스트용 고정 텍스트 반환
    return {"ok": True, "text": "stub response", "model": req.model or "stub", "usage": {}}
