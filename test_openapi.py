# test_openapi.py
import os

from dotenv import load_dotenv
from openai import OpenAI

# 프로젝트 루트의 .env 파일 명시
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

api_key = os.getenv("OPENAI_API_KEY")
model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
client = OpenAI(api_key=api_key)

response = client.responses.create(
    model=model,
    input="간단한 테스트 문장을 입력해 주세요."
)

print(response.output_text)