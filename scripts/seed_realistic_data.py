"""현실적인 테스트 데이터 생성 스크립트.

프론트엔드 개발을 위한 현실적인 더미 데이터를 생성합니다.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import Document, Project, Task

# 현실적인 프로젝트 데이터
REALISTIC_PROJECTS = [
    {
        "title": "AI 기반 효율적 개발 플랫폼",
        "content_md": """# AI 기반 효율적 개발 플랫폼

## 프로젝트 개요
AI를 활용하여 개발 프로세스를 자동화하고 효율성을 높이는 통합 개발 플랫폼입니다.

## 주요 기능
- PRD/SRS 문서 자동 생성
- 사용자 스토리 기반 태스크 분해
- AI 기반 코드 생성 및 리뷰
- MCP(Model Context Protocol) 연동

## 기술 스택
- Backend: FastAPI, Python 3.11+
- Frontend: React, TypeScript
- Database: Oracle
- AI: OpenAI GPT-4, Claude 3
""",
    },
    {
        "title": "실시간 협업 문서 편집기",
        "content_md": """# 실시간 협업 문서 편집기

## 프로젝트 개요
여러 사용자가 동시에 문서를 편집하고 실시간으로 변경사항을 확인할 수 있는 웹 애플리케이션입니다.

## 주요 기능
- 실시간 동시 편집 (Operational Transform)
- 버전 관리 및 히스토리
- 댓글 및 피드백 시스템
- 마크다운 지원

## 기술 스택
- Frontend: React, Socket.io
- Backend: Node.js, Express
- Database: PostgreSQL
""",
    },
]

# 현실적인 태스크 데이터
REALISTIC_TASKS = [
    {
        "title": "사용자 인증 시스템 구현",
        "description": "JWT 기반 토큰 인증 및 OAuth 2.0 소셜 로그인 기능 구현",
        "description_md": """## 작업 내용
- JWT 토큰 발급 및 검증 로직 구현
- Google, GitHub OAuth 2.0 연동
- 리프레시 토큰 관리
- 보안 미들웨어 추가

## 완료 조건
- [ ] JWT 토큰 발급/검증 API 완성
- [ ] OAuth 콜백 처리 구현
- [ ] 단위 테스트 작성
- [ ] API 문서화
""",
        "type": "dev",
        "status": "in_progress",
        "priority": 8,
        "assigned_role": "Backend",
        "tags": ["인증", "보안"],
    },
    {
        "title": "프로젝트 대시보드 UI 개발",
        "description": "프로젝트 목록, 통계, 최근 활동을 보여주는 대시보드 페이지 구현",
        "description_md": """## 작업 내용
- 프로젝트 카드 컴포넌트 디자인
- 통계 차트 (완료율, 진행률)
- 최근 활동 피드
- 반응형 레이아웃

## 완료 조건
- [ ] 디자인 시스템 적용
- [ ] API 연동 완료
- [ ] 모바일 반응형 구현
- [ ] 접근성 검사 통과
""",
        "type": "dev",
        "status": "todo",
        "priority": 7,
        "assigned_role": "Frontend",
        "tags": ["UI", "대시보드"],
    },
    {
        "title": "PRD 문서 작성 - 사용자 관리 기능",
        "description": "사용자 등록, 프로필 관리, 권한 설정 기능에 대한 PRD 문서 작성",
        "description_md": """## 문서 목차
1. 기능 개요
2. 사용자 시나리오
3. 기능 요구사항
4. 비기능 요구사항
5. UI/UX 가이드라인

## 주요 기능
- 사용자 등록/로그인
- 프로필 수정
- 권한 관리 (Admin, User, Guest)
""",
        "type": "docs",
        "status": "review",
        "priority": 6,
        "assigned_role": None,
        "tags": ["문서", "PRD"],
    },
    {
        "title": "데이터베이스 스키마 최적화",
        "description": "쿼리 성능 개선을 위한 인덱스 추가 및 테이블 구조 최적화",
        "description_md": """## 최적화 대상
- tasks 테이블 인덱스 추가
- N+1 쿼리 문제 해결
- 조인 쿼리 최적화

## 예상 효과
- 목록 조회 속도 50% 개선
- 복잡한 쿼리 응답 시간 단축
""",
        "type": "dev",
        "status": "todo",
        "priority": 5,
        "assigned_role": "Backend",
        "tags": ["성능", "DB"],
    },
    {
        "title": "API 에러 핸들링 개선",
        "description": "일관된 에러 응답 형식 및 에러 코드 체계 구축",
        "description_md": """## 개선 사항
- 표준 에러 응답 형식 정의
- HTTP 상태 코드 매핑
- 에러 로깅 및 모니터링 연동

## 에러 코드 체계
- 4xx: 클라이언트 오류
- 5xx: 서버 오류
- 커스텀 에러 코드 정의
""",
        "type": "dev",
        "status": "in_progress",
        "priority": 6,
        "assigned_role": "Backend",
        "tags": ["에러처리", "API"],
    },
    {
        "title": "컴포넌트 라이브러리 구축",
        "description": "재사용 가능한 React 컴포넌트 라이브러리 개발",
        "description_md": """## 컴포넌트 목록
- Button, Input, Select
- Modal, Toast, Tooltip
- Table, Pagination
- Form 컴포넌트

## 기술 스택
- React 18
- TypeScript
- Storybook
- Tailwind CSS
""",
        "type": "dev",
        "status": "todo",
        "priority": 7,
        "assigned_role": "Frontend",
        "tags": ["컴포넌트", "라이브러리"],
    },
]

# 현실적인 문서 데이터
REALISTIC_DOCUMENTS = [
    {
        "type": "PRD",
        "title": "사용자 인증 및 권한 관리 기능 PRD",
        "content_md": """# Product Requirements Document: 사용자 인증 및 권한 관리

## 1. 개요
본 문서는 플랫폼의 사용자 인증 및 권한 관리 기능에 대한 요구사항을 정의합니다.

## 2. 목표
- 안전하고 편리한 사용자 인증 제공
- 세밀한 권한 관리로 보안 강화
- 다양한 인증 방식 지원

## 3. 기능 요구사항

### 3.1 사용자 등록
- 이메일/비밀번호 기반 회원가입
- 소셜 로그인 (Google, GitHub)
- 이메일 인증

### 3.2 로그인
- 이메일/비밀번호 로그인
- 소셜 로그인
- 2단계 인증 (선택)

### 3.3 권한 관리
- 역할 기반 접근 제어 (RBAC)
- 역할: Admin, Developer, Viewer
- 프로젝트별 권한 설정

## 4. 비기능 요구사항
- 보안: OWASP Top 10 준수
- 성능: 로그인 응답 시간 < 500ms
- 가용성: 99.9% uptime
""",
    },
    {
        "type": "SRS",
        "title": "사용자 인증 시스템 기술 명세서",
        "content_md": """# Software Requirements Specification: 사용자 인증 시스템

## 1. 시스템 개요
JWT 기반 토큰 인증과 OAuth 2.0을 지원하는 사용자 인증 시스템입니다.

## 2. 아키텍처
- 인증 서버: FastAPI 기반 REST API
- 토큰 저장: HTTP-only Cookie 또는 LocalStorage
- 세션 관리: Redis (선택)

## 3. 기술 스택
- Backend: FastAPI, Python
- 인증 라이브러리: python-jose, passlib
- OAuth: authlib

## 4. API 명세

### POST /api/v1/auth/register
사용자 등록 엔드포인트

### POST /api/v1/auth/login
로그인 엔드포인트

### POST /api/v1/auth/refresh
토큰 갱신 엔드포인트

## 5. 보안 요구사항
- 비밀번호 해싱: bcrypt
- 토큰 만료 시간: 15분 (액세스), 7일 (리프레시)
- HTTPS 필수
""",
    },
    {
        "type": "USER_STORY",
        "title": "사용자 인증 관련 사용자 스토리",
        "content_md": """# User Stories: 사용자 인증

## Story 1: 회원가입
**As a** 새로운 사용자  
**I want to** 이메일과 비밀번호로 회원가입을 할 수 있어야 합니다  
**So that** 플랫폼을 이용할 수 있습니다

**Acceptance Criteria:**
- 이메일 형식 검증
- 비밀번호 강도 검사 (최소 8자, 대소문자, 숫자 포함)
- 중복 이메일 체크
- 이메일 인증 메일 발송

## Story 2: 소셜 로그인
**As a** 사용자  
**I want to** Google 계정으로 로그인할 수 있어야 합니다  
**So that** 별도의 회원가입 없이 빠르게 시작할 수 있습니다

**Acceptance Criteria:**
- Google OAuth 2.0 연동
- 사용자 정보 자동 동기화
- 기존 계정과 연동 가능

## Story 3: 권한 관리
**As a** 프로젝트 관리자  
**I want to** 팀원에게 프로젝트별 권한을 부여할 수 있어야 합니다  
**So that** 보안을 유지하면서 협업할 수 있습니다

**Acceptance Criteria:**
- 역할별 권한 설정 UI
- 실시간 권한 변경 반영
- 권한 변경 이력 기록
""",
    },
]


def seed_realistic_data(db: Session, project_id: int = 148):
    """현실적인 테스트 데이터를 생성합니다."""
    print(f"프로젝트 ID {project_id}에 현실적인 데이터 생성 중...")

    # 프로젝트 업데이트
    project = db.query(Project).filter(Project.id == project_id).first()
    if project:
        if len(REALISTIC_PROJECTS) > 0:
            proj_data = REALISTIC_PROJECTS[0]
            project.title = proj_data["title"]
            project.content_md = proj_data["content_md"]
            db.add(project)
            print(f"✓ 프로젝트 업데이트: {project.title}")

    # 기존 태스크 삭제 (선택사항 - 주석 처리하면 추가만 함)
    # db.query(Task).filter(Task.project_id == project_id).delete()

    # 태스크 생성
    created_tasks = []
    for task_data in REALISTIC_TASKS:
        task = Task(
            project_id=project_id,
            title=task_data["title"],
            description=task_data["description"],
            description_md=task_data["description_md"],
            type=task_data["type"],
            status=task_data["status"],
            priority=task_data["priority"],
            assigned_role=task_data["assigned_role"],
            tags=str(task_data["tags"]) if task_data.get("tags") else None,
            created_at=datetime.now() - timedelta(days=len(created_tasks)),
            updated_at=datetime.now() - timedelta(hours=len(created_tasks)),
        )
        db.add(task)
        created_tasks.append(task)
        print(f"✓ 태스크 생성: {task.title} ({task.status})")

    # 문서 생성
    for doc_data in REALISTIC_DOCUMENTS:
        # 기존 문서가 있으면 업데이트, 없으면 생성
        existing_doc = (
            db.query(Document)
            .filter(
                Document.project_id == project_id,
                Document.type == doc_data["type"],
                Document.title == doc_data["title"],
            )
            .first()
        )

        if existing_doc:
            existing_doc.content_md = doc_data["content_md"]
            existing_doc.updated_at = datetime.now()
            db.add(existing_doc)
            print(f"✓ 문서 업데이트: {existing_doc.title}")
        else:
            doc = Document(
                project_id=project_id,
                type=doc_data["type"],
                title=doc_data["title"],
                content_md=doc_data["content_md"],
                author_id="system",
                last_editor_id="system",
                status="done",
            )
            db.add(doc)
            print(f"✓ 문서 생성: {doc.title}")

    db.commit()
    print(f"\n✅ 총 {len(created_tasks)}개 태스크, {len(REALISTIC_DOCUMENTS)}개 문서 생성/업데이트 완료!")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_realistic_data(db, project_id=148)
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        db.rollback()
        raise
    finally:
        db.close()

