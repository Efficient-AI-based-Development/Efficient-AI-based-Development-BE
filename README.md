# Efficient AI Backend

AI 기반 효율적인 개발을 위한 백엔드 시스템

## 🛠 기술 스택

- **Backend**: Python 3.10+, FastAPI 3.x
- **Database**: Oracle (oracledb 드라이버)
- **ORM**: SQLAlchemy 2.x + Alembic
- **Validation**: Pydantic v2
- **Testing**: pytest, httpx
- **Linting**: Ruff
- **Formatting**: Black
- **Type Checking**: MyPy
- **Package Manager**: UV
- **Infrastructure**: Docker, GitHub Actions CI/CD
- **Docs**: FastAPI 자동 OpenAPI (Swagger UI / ReDoc)

## 🧰 환경 설정

### 사전 요구사항

- Python 3.11 이상
- Oracle Database
- UV 패키지 매니저

### 1. 저장소 클론

```bash
git clone <repository-url>
cd efficient-ai-backend
```

### 2. UV 설치 (필요한 경우)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. 프로젝트 의존성 설치

```bash
uv sync
```

### 4. Pre-commit 설치

```bash
pre-commit install
```

### 5. 환경 변수 설정

`.env` 파일을 생성하고 Oracle 데이터베이스 연결 정보를 설정합니다:

```bash
cp env.example .env
```

`.env` 파일 예시:

```env
DATABASE_URL=oracle+oracledb://user:password@host:1521/service
DEBUG=false
LOG_LEVEL=INFO
API_PREFIX=/api/v1
# fastMCP 연동 (ChatGPT MCP용)
FASTMCP_BASE_URL=http://localhost:8787
FASTMCP_TOKEN=project-fastmcp-token-1234
OPENAI_MODEL=gpt-4o-mini
```

fastMCP 서버는 저장소 내 `fastmcp-fastapi` 예제를 사용할 수 있습니다.

```bash
cd fastmcp-fastapi
# .env 파일을 생성하고 아래 값을 참고해 설정합니다.
uv run uvicorn fastmcp-fastapi.server:app --reload --port 8787
```

`fastmcp-fastapi/.env` 예시:

```env
FASTMCP_TOKEN=project-fastmcp-token-1234
FASTMCP_MODE=mock  # mock | real
OPENAI_API_KEY=sk-your-openai-api-key
ANTHROPIC_API_KEY=sk-your-anthropic-api-key
PORT=8787
```

`FASTMCP_TOKEN` 값은 백엔드 `.env`의 값과 동일하게 맞춰 주세요.

### 6. 데이터베이스 마이그레이션

```bash
# 초기 마이그레이션 생성
alembic revision --autogenerate -m "Initial migration"

# 마이그레이션 실행
alembic upgrade head
```

## 🚀 실행/테스트

### 서버 실행

```bash
uv run uvicorn app.main:app --reload
```

또는 직접 Python으로:

```bash
uv run python -m app.main
```

### 서버 접속

- API 문서: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health Check: http://localhost:8000/health

### 테스트 실행

```bash
# 전체 테스트
uv run pytest

# verbose 모드
uv run pytest -v

# 특정 테스트만
uv run pytest tests/test_routes/test_projects.py

# 커버리지 포함
uv run pytest --cov=app --cov-report=html
```

### 코드 품질 검사

```bash
# Ruff 린팅
uv run ruff check app/

# Black 포맷팅
uv run black app/

# MyPy 타입 체크
uv run mypy app/
```

## 📁 프로젝트 구조

```
efficient-ai-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI 애플리케이션 진입점
│   ├── core/                      # 핵심 설정 및 유틸리티
│   │   ├── config.py              # 설정 관리 (Pydantic Settings)
│   │   ├── logging.py             # 로깅 설정
│   │   ├── cors.py                # CORS 설정
│   │   └── exceptions.py          # 에러 핸들러
│   ├── db/                        # 데이터베이스 관련
│   │   ├── database.py            # DB 연결 및 세션 관리
│   │   └── models.py               # SQLAlchemy 모델 (Oracle 전용)
│   ├── api/                       # API 관련
│   │   └── v1/
│   │       └── routes/            # API 라우터들
│   │           ├── projects.py    # 프로젝트 CRUD
│   │           ├── documents.py    # 문서 CRUD
│   │           ├── generate.py    # 생성 작업
│   │           ├── tasks.py       # 태스크 CRUD
│   │           ├── insights.py    # 인사이트
│   │           └── mcp.py         # MCP 프로토콜
│   └── schemas/                   # Pydantic 스키마
│       ├── project.py
│       ├── document.py
│       ├── task.py
│       ├── generation.py
│       ├── insight.py
│       ├── chat.py
│       └── mcp.py
├── alembic/                       # 데이터베이스 마이그레이션
│   ├── env.py                     # 마이그레이션 환경 설정
│   └── versions/                  # 마이그레이션 버전들
├── tests/                         # 테스트 코드
│   ├── conftest.py                # pytest 설정
│   ├── test_main.py                # 메인 앱 테스트
│   └── test_routes/               # 라우터 테스트들
├── .github/workflows/ci.yml       # CI/CD 파이프라인
├── Dockerfile                     # Docker 이미지 빌드
├── pyproject.toml                 # 프로젝트 설정
├── alembic.ini                    # Alembic 설정
├── env.example                    # 환경 변수 예시
└── README.md                      # 프로젝트 문서
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
- feat/_, fix/_, chore/\* 분기 → PR → 리뷰 → squash merge

## 🔐 보안

- 입력 검증: **Pydantic(BaseModel)**으로 모든 요청 데이터 타입/제약 검사
- 비밀키/DB 정보는 .env로 관리 (커밋 금지)
  “.env는 반드시 .gitignore에 포함, 공유는 .env.example로만 진행”
- 민감 정보 로그 출력 금지

## 📦 Docker 사용

### 이미지 빌드

```bash
docker build -t efficient-ai-backend .
```

### 컨테이너 실행

```bash
docker run -p 8000:8000 --env-file .env efficient-ai-backend
```

## 🔄 CI/CD

GitHub Actions를 통해 자동화된 CI/CD 파이프라인이 설정되어 있습니다:

- **Lint**: Ruff로 코드 품질 검사
- **Format**: Black으로 포맷팅 체크
- **Type Check**: MyPy로 타입 체크
- **Test**: Pytest로 테스트 실행
- **Migration Check**: Alembic 마이그레이션 검증
- **Build**: Docker 이미지 빌드

## 📜 API 명세

FastAPI 자동 생성 문서 확인:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 주요 엔드포인트

#### 프로젝트 (Projects)

```bash
GET    /api/v1/projects              # 목록 조회
POST   /api/v1/projects              # 생성
GET    /api/v1/projects/{id}         # 조회
PATCH  /api/v1/projects/{id}         # 수정
DELETE /api/v1/projects/{id}         # 삭제
```

#### 문서 (Documents)

```bash
POST   /api/v1/docs/{id}/rewrite     # AI 문서 수정
POST   /api/v1/docs/{id}/rewrite/full # AI 문서 전체 수정
GET    /api/v1/docs/{id}             # 조회
PATCH  /api/v1/docs/{id}             # 수정
DELETE /api/v1/docs/{id}             # 삭제
```

#### 태스크 (Tasks)

```bash
POST   /api/v1/projects/{id}/tasks   # 생성
GET    /api/v1/projects/{id}/tasks   # 목록
GET    /api/v1/tasks/{id}            # 조회
PATCH  /api/v1/tasks/{id}            # 수정
DELETE /api/v1/tasks/{id}            # 삭제
```

#### MCP (Model Context Protocol)

```bash
POST   /api/mcp/connections          # 연결 생성
GET    /api/mcp/connections          # 연결 목록
DELETE /api/mcp/connections/{id}     # 연결 종료
POST   /api/mcp/sessions            # 세션 시작
GET    /api/mcp/sessions            # 세션 목록
GET    /api/mcp/tools               # 툴 카탈로그
GET    /api/mcp/resources            # 리소스 카탈로그
GET    /api/mcp/prompts              # 프롬프트 카탈로그
POST   /api/mcp/runs                # 실행 생성
GET    /api/mcp/runs/{id}           # 실행 상태
GET    /api/mcp/runs/{id}/events    # SSE 이벤트 스트리밍
```
