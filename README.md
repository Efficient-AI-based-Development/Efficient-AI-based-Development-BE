# Efficient-AI-based-Development-BE

## 🛠 기술 스택
- Backend: Python 3.10+, FastAPI, SQLAlchemy
- DB: Oracle
- Infra/Tooling: Alembic(마이그레이션), Pydantic v2, Uvicorn, pre-commit, etc
- test : pytest
- Docs: FastAPI 자동 OpenAPI(Swagger UI / Redoc)

## 🧰 환경 설정
```
# 1) 가상환경 생성 및 활성화
python -m venv .venv

# macOS/Linux
source .venv/bin/activate

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1


# 2) 패키지 설치
pip install -r requirements.txt


# 3) 환경 변수 설정
cp .env.example .env             # 실제 값으로 수정 후 사용
```

## 실행/테스트
```
# 서버 실행
uvicorn app.main:app --reload

# 테스트 실행
pytest              # 전체 실행
pytest -q           # 조용히
pytest tests/test_calc.py::test_add   # 특정 테스트만
```


## 📁 프로젝트 구조
```
.
├─ app/
│  ├─ main.py
│  ├─ api/
│  │   └─ v1/
│  │       └─ router.py          # v1 라우터 허브(도메인 라우터 묶음)
│  ├─ common/
│  │   └─ deps.py                # 공통 의존성 주입 (DB 세션 등)
│  ├─ core/
│  │   └─ __init__.py            # 설정/초기화 (config, logging 등 추가 예정)
│  └─ domains/                   # 도메인별 공통 구조
│      ├─ chat_message/
│      ├─ chat_session/
│      ├─ document/
│      ├─ document_version/
│      ..
│      └─ project/
│          ├─ model.py
│          ├─ repo.py            # DB 접근
│          ├─ router.py          # API 엔드포인트
│          ├─ schema.py          # Pydantic 모델
│          └─ service.py         # 비즈니스 로직
│
├─ db/
│  ├─ base.py                     # Base 클래스 정의
│  ├─ session.py                  # DB 세션 연결 설정
│  └─ __init__.py
├─ .env
└─ .env.example

```

## 📝 커밋/브랜치 규칙
- Conventional Commits
```
init: 프로젝트 초기화
feat: 새로운 기능 추가
fix: 버그 수정
docs: 문서 수정
style: 코드 포매팅/세미콜론 등, 로직 변경 없음
refactor: 코드 리팩토링(동작 변화 없음)
test: 테스트 코드 추가/개선
chore: 빌드/의존성/환경설정 변경
minor: 사소한 변경 (선택)
```

## 🌿브랜칭
- main: 배포 브랜치
- dev: 개발 브랜치
- feat/*, fix/*, chore/* 분기 → PR → 리뷰 → squash merge

## 🔐 보안
- 입력 검증: **Pydantic(BaseModel)**으로 모든 요청 데이터 타입/제약 검사
- 비밀키/DB 정보는 .env로 관리 (커밋 금지)
“.env는 반드시 .gitignore에 포함, 공유는 .env.example로만 진행”
- 민감 정보 로그 출력 금지

## 📜 API 명세
- FastAPI 자동 문서 확인
  - Swagger: http://localhost:8000/docs
  - Redoc: http://localhost:8000/redoc

- 주요 엔드포인트 예시:
```
GET    /api/v1/projects
POST   /api/v1/projects
GET    /api/v1/projects/{projectID}
PATCH  /api/v1/projects/{projectID}
DELETE /api/v1/projects/{projectID}
```
