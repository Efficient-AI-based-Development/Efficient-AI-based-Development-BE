#!/usr/bin/env python3
"""USER_STORY 문서 생성 스크립트"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.db.models import Document, Project, User
from app.core.config import settings

def create_user_story_document(project_id: int):
    """USER_STORY 문서 생성"""
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

        # 기존 USER_STORY 문서 확인
        existing = (
            db.query(Document)
            .filter(
                Document.project_id == project_id,
                Document.type == "USER_STORY",
            )
            .first()
        )

        user_story_content = """# MCP Quick Test 프로젝트 - User Stories

## Story 1: MCP 서버 연결
**As a** 개발자  
**I want to** MCP 서버에 연결할 수 있어야 합니다  
**So that** MCP 툴을 사용할 수 있습니다

### Acceptance Criteria:
- 서버 URL을 설정할 수 있어야 함
- 인증 토큰을 설정할 수 있어야 함
- 연결 상태를 확인할 수 있어야 함
- 연결 실패 시 명확한 오류 메시지를 표시해야 함

---

## Story 2: 툴 목록 조회
**As a** 개발자  
**I want to** 사용 가능한 MCP 툴 목록을 조회할 수 있어야 합니다  
**So that** 어떤 툴을 사용할 수 있는지 알 수 있습니다

### Acceptance Criteria:
- 툴 목록을 가져올 수 있어야 함
- 각 툴의 이름과 설명을 볼 수 있어야 함
- 툴이 없을 경우 적절한 메시지를 표시해야 함

---

## Story 3: 툴 실행
**As a** 개발자  
**I want to** 특정 MCP 툴을 실행할 수 있어야 합니다  
**So that** 원하는 작업을 수행할 수 있습니다

### Acceptance Criteria:
- 툴 ID로 툴을 실행할 수 있어야 함
- 툴 실행 결과를 받을 수 있어야 함
- 실행 실패 시 오류 정보를 받을 수 있어야 함

---

## Story 4: 에러 처리
**As a** 개발자  
**I want to** 발생한 오류를 명확하게 파악할 수 있어야 합니다  
**So that** 문제를 빠르게 해결할 수 있습니다

### Acceptance Criteria:
- 연결 오류를 명확히 표시해야 함
- 툴 실행 오류를 명확히 표시해야 함
- 사용자 친화적인 오류 메시지를 제공해야 함
"""

        if existing:
            # 기존 문서 업데이트
            existing.title = "MCP Quick Test 프로젝트 User Stories"
            existing.content_md = user_story_content
            existing.last_editor_id = user.user_id
            print(f"✅ USER_STORY 문서 업데이트 완료 (ID: {existing.id})")
        else:
            # 새 문서 생성
            document = Document(
                project_id=project_id,
                author_id=user.user_id,
                last_editor_id=user.user_id,
                type="USER_STORY",
                title="MCP Quick Test 프로젝트 User Stories",
                content_md=user_story_content,
            )
            db.add(document)
            print(f"✅ USER_STORY 문서 생성 완료")

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
    print(f"프로젝트 {project_id}에 USER_STORY 문서 생성 중...")
    success = create_user_story_document(project_id)
    if success:
        print("✅ 완료!")
        sys.exit(0)
    else:
        print("❌ 실패!")
        sys.exit(1)

