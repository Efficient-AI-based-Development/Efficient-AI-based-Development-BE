#!/usr/bin/env python3
"""PRD 문서 생성 스크립트"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.db.models import Document, Project, User
from app.core.config import settings

def create_prd_document(project_id: int):
    """PRD 문서 생성"""
    db: Session = SessionLocal()
    try:
        # 프로젝트 확인
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            print(f"❌ 프로젝트를 찾을 수 없습니다: {project_id}")
            return False

        # 사용자 확인 (디버그 모드에서는 첫 번째 사용자 사용)
        if settings.debug:
            user = db.query(User).first()
            if not user:
                print("❌ 사용자를 찾을 수 없습니다. 사용자를 먼저 생성하세요.")
                return False
        else:
            # 프로덕션에서는 프로젝트 소유자 사용
            user = db.query(User).filter(User.user_id == project.owner_id).first()
            if not user:
                print(f"❌ 프로젝트 소유자를 찾을 수 없습니다: {project.owner_id}")
                return False

        # 기존 PRD 문서 확인
        existing = (
            db.query(Document)
            .filter(
                Document.project_id == project_id,
                Document.type == "PRD",
            )
            .first()
        )

        prd_content = """# MCP Quick Test 프로젝트 - Product Requirements Document

## 1. 프로젝트 개요

### 1.1 목적
MCP (Model Context Protocol) 연동 기능을 테스트하고 검증하기 위한 간단한 Node.js 프로젝트를 개발합니다.

### 1.2 배경
- MCP 프로토콜의 기본 기능 이해
- MCP 서버와의 통신 방법 학습
- 실제 사용 사례 구현

## 2. 기능 요구사항

### 2.1 핵심 기능
1. **MCP 서버 연결**
   - 서버 URL 및 인증 정보 설정
   - 연결 상태 확인

2. **툴 목록 조회**
   - 사용 가능한 MCP 툴 목록 가져오기
   - 툴 메타데이터 표시

3. **툴 실행**
   - 특정 툴 실행
   - 실행 결과 처리

4. **에러 처리**
   - 연결 오류 처리
   - 실행 오류 처리
   - 사용자 친화적 오류 메시지

### 2.2 부가 기능
- 로깅 기능
- 설정 파일 관리
- 테스트 코드

## 3. 기술 요구사항

### 3.1 기술 스택
- **런타임**: Node.js v18 이상
- **언어**: TypeScript (권장) 또는 JavaScript
- **테스트**: Jest
- **패키지 관리**: npm 또는 yarn

### 3.2 의존성
- MCP SDK 또는 클라이언트 라이브러리
- HTTP 클라이언트 (axios, fetch 등)

## 4. 프로젝트 구조

```
project/
├── src/
│   ├── client.ts          # MCP 클라이언트 메인 클래스
│   ├── tools.ts            # 툴 관리 모듈
│   ├── types.ts            # TypeScript 타입 정의
│   └── index.ts            # 진입점
├── tests/
│   ├── client.test.ts      # 클라이언트 테스트
│   └── tools.test.ts       # 툴 관리 테스트
├── config/
│   └── default.json        # 기본 설정
├── package.json
├── tsconfig.json
├── jest.config.js
└── README.md
```

## 5. 성공 기준

### 5.1 기능적 요구사항
- [ ] MCP 서버에 성공적으로 연결
- [ ] 툴 목록을 정상적으로 조회
- [ ] 툴을 성공적으로 실행
- [ ] 에러 상황을 적절히 처리

### 5.2 비기능적 요구사항
- [ ] 코드 커버리지 80% 이상
- [ ] 모든 테스트 통과
- [ ] README 문서 완성
- [ ] 타입 안정성 확보 (TypeScript 사용 시)

## 6. 제약사항

- MCP 서버는 외부에서 제공됨
- 인증 토큰은 환경 변수로 관리
- 프로젝트는 독립적으로 실행 가능해야 함

## 7. 향후 확장 계획

- GUI 인터페이스 추가
- 더 많은 MCP 툴 지원
- 배치 실행 기능
- 결과 캐싱
"""

        if existing:
            # 기존 문서 업데이트
            existing.title = "MCP Quick Test 프로젝트 PRD"
            existing.content_md = prd_content
            existing.last_editor_id = user.user_id
            print(f"✅ PRD 문서 업데이트 완료 (ID: {existing.id})")
        else:
            # 새 문서 생성
            document = Document(
                project_id=project_id,
                author_id=user.user_id,
                last_editor_id=user.user_id,
                type="PRD",
                title="MCP Quick Test 프로젝트 PRD",
                content_md=prd_content,
            )
            db.add(document)
            print(f"✅ PRD 문서 생성 완료")

        db.commit()
        return True

    except Exception as e:
        db.rollback()
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    project_id = 148
    print(f"프로젝트 {project_id}에 PRD 문서 생성 중...")
    success = create_prd_document(project_id)
    if success:
        print("✅ 완료!")
        sys.exit(0)
    else:
        print("❌ 실패!")
        sys.exit(1)

