"""SQLAlchemy models for Oracle database.

이 파일에는 Oracle 데이터베이스에 생성될 모든 테이블의 모델이 정의되어 있습니다.

Oracle 전용 설계 특징:
1. ENUM 대신 VARCHAR2 + CHECK 제약조건 사용
2. 긴 텍스트는 CLOB 타입 사용
3. PK는 IDENTITY 컬럼 사용 (Oracle 12c+)
4. 타임스탬프는 TIMESTAMP 사용

주의사항:
- Oracle은 Python의 datetime과 잘 작동하지만, 타임존 설정에 주의
- VARCHAR2는 최대 4000바이트 (CLOB은 무제한)
"""

from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    CheckConstraint, CLOB, func, UniqueConstraint, Index,
)
from sqlalchemy.orm import relationship

from app.db.database import Base


class Project(Base):
    """프로젝트 모델
    
    AI 개발 프로젝트의 기본 정보를 저장합니다.
    
    Attributes:
        id: 프로젝트 고유 ID (IDENTITY - 자동 증가)
        name: 프로젝트 이름 (VARCHAR2)
        description: 프로젝트 설명 (CLOB)
        status: 프로젝트 상태 (VARCHAR2 + CHECK: 'active', 'completed', 'archived')
        created_at: 생성 시간
        updated_at: 수정 시간
    
    Relationships:
        - documents: 프로젝트에 속한 문서들
        - tasks: 프로젝트에 속한 태스크들
        - gen_jobs: 프로젝트의 생성 작업들
    """

    __tablename__ = "projects"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="프로젝트 고유 ID",
    )
    name = Column(
        String(255),
        nullable=False,
        comment="프로젝트 이름",
    )
    description = Column(
        Text,
        comment="프로젝트 설명",
    )
    status = Column(
        String(50),
        nullable=False,
        default="active",
        comment="프로젝트 상태",
    )
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="생성 시간",
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="수정 시간",
    )

    # Relationships
    documents = relationship("Document", back_populates="project")
    tasks = relationship("Task", back_populates="project")
    gen_jobs = relationship("GenJob", back_populates="project")

    # Check constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'completed', 'archived')",
            name="chk_project_status",
        ),
    )


class Document(Base):
    """문서 모델
    
    프로젝트의 문서(PRD, UserStory, SRS 등)를 저장합니다.
    
    Attributes:
        id: 문서 고유 ID
        project_id: 프로젝트 외래키
        type: 문서 타입 (VARCHAR2 + CHECK: 'PRD', 'UserStory', 'SRS')
        title: 문서 제목
        content_md: 문서 내용 (CLOB - 긴 텍스트 저장)
        author_id: 만든 사람
        last_editor_id: 최근 수정 사람
        created_at: 생성 시간
        updated_at: 수정 시간
    
    Relationships:
        - project: 소속 프로젝트
    """
    __tablename__ = 'documents'

    id = Column(Integer, primary_key=True)
    project_id = Column(
        Integer,
        ForeignKey('projects.id', ondelete='CASCADE'),  # FK + 삭제시 CASCADE
        nullable=False
    )
    type = Column(String(20), nullable=False)
    title = Column(String(300), nullable=False)
    content_md = Column(CLOB)
    author_id = Column(String(120), nullable=False)
    last_editor_id = Column(String(120), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),  # Oracle의 DEFAULT SYSTIMESTAMP 대응
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=True,  # DDL에서도 nullable임
        onupdate=func.now()  # UPDATE 시 자동 갱신
    )

    # 테이블 제약 조건 및 인덱스
    __table_args__ = (
        CheckConstraint(
            "type IN ('PRD','USER_STORY','TRD')",
            name='ck_documents_type'
        ),
        UniqueConstraint('project_id', 'title', name='uq_documents_project_title'),
        Index('ix_documents_project_type', 'project_id', 'type'),
    )

    project = relationship(
        "Project",
        back_populates="documents",
    )


class Task(Base):
    """태스크 모델
    
    프로젝트의 개발 태스크(기능, 버그, 기타)를 관리합니다.
    
    Attributes:
        id: 태스크 ID
        project_id: 프로젝트 외래키
        title: 태스크 제목
        description: 태스크 설명 (CLOB)
        status: 태스크 상태 (VARCHAR2 + CHECK: 'pending', 'in_progress', 'completed', 'blocked')
        priority: 우선순위 (VARCHAR2 + CHECK: 'low', 'medium', 'high', 'urgent')
        created_at: 생성 시간
        updated_at: 수정 시간
    
    Relationships:
        - project: 소속 프로젝트
        - parent_links: 이 태스크를 부모로 하는 링크들
        - child_links: 이 태스크를 자식으로 하는 링크들
    """

    __tablename__ = "tasks"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="태스크 ID",
    )
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        comment="프로젝트 외래키",
    )
    title = Column(
        String(500),
        nullable=False,
        comment="태스크 제목",
    )
    description = Column(
        Text,
        comment="태스크 설명 (CLOB)",
    )
    status = Column(
        String(50),
        nullable=False,
        default="pending",
        comment="태스크 상태",
    )
    priority = Column(
        String(50),
        nullable=False,
        default="medium",
        comment="우선순위",
    )
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="생성 시간",
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="수정 시간",
    )

    # Relationships
    project = relationship("Project", back_populates="tasks")
    parent_links = relationship(
        "TaskLink",
        foreign_keys="TaskLink.parent_task_id",
        back_populates="parent_task",
    )
    child_links = relationship(
        "TaskLink",
        foreign_keys="TaskLink.child_task_id",
        back_populates="child_task",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'in_progress', 'completed', 'blocked')",
            name="chk_task_status",
        ),
        CheckConstraint(
            "priority IN ('low', 'medium', 'high', 'urgent')",
            name="chk_task_priority",
        ),
    )


class TaskLink(Base):
    """태스크 링크 모델
    
    태스크 간의 의존성 관계를 관리합니다.
    
    Attributes:
        id: 링크 ID
        parent_task_id: 부모 태스크 ID (이 태스크를 먼저 완료해야 함)
        child_task_id: 자식 태스크 ID (부모가 완료되면 시작 가능)
        link_type: 링크 타입 (VARCHAR2 + CHECK: 'blocks', 'depends_on', 'relates_to')
        created_at: 생성 시간
    
    설명:
        - blocks: 부모 태스크가 완료되지 않으면 자식 태스크를 시작할 수 없음
        - depends_on: 자식 태스크가 부모 태스크에 의존함
        - relates_to: 두 태스크가 관련됨 (순서 제약 없음)
    """

    __tablename__ = "task_links"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="링크 ID",
    )
    parent_task_id = Column(
        Integer,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        comment="부모 태스크 ID",
    )
    child_task_id = Column(
        Integer,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        comment="자식 태스크 ID",
    )
    link_type = Column(
        String(50),
        nullable=False,
        comment="링크 타입",
    )
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="생성 시간",
    )

    # Relationships
    parent_task = relationship("Task", foreign_keys=[parent_task_id], back_populates="parent_links")
    child_task = relationship("Task", foreign_keys=[child_task_id], back_populates="child_links")

    __table_args__ = (
        CheckConstraint(
            "link_type IN ('blocks', 'depends_on', 'relates_to')",
            name="chk_task_link_type",
        ),
        CheckConstraint(
            "parent_task_id != child_task_id",
            name="chk_no_self_link",
        ),
    )


class GenJob(Base):
    """생성 작업 모델
    
    AI 기반 코드 생성 작업의 상태와 결과를 추적합니다.
    
    Attributes:
        id: 작업 ID
        project_id: 프로젝트 외래키
        job_type: 작업 타입 (VARCHAR2 + CHECK: 'code_generation', 'document_generation', 'test_generation')
        status: 작업 상태 (VARCHAR2 + CHECK: 'pending', 'running', 'completed', 'failed', 'cancelled')
        result: 생성 결과 (CLOB)
        created_at: 생성 시간
        updated_at: 수정 시간
    
    설명:
        - AI 생성 작업의 전체 라이프사이클을 추적
        - 결과는 CLOB으로 저장하여 대용량 결과도 저장 가능
        - 실패한 작업은 에러 메시지를 result에 저장
    """

    __tablename__ = "gen_jobs"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="작업 ID",
    )
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        comment="프로젝트 외래키",
    )
    job_type = Column(
        String(100),
        nullable=False,
        comment="작업 타입",
    )
    status = Column(
        String(50),
        nullable=False,
        default="pending",
        comment="작업 상태",
    )
    result = Column(
        Text,
        comment="생성 결과 (CLOB)",
    )
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="생성 시간",
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="수정 시간",
    )

    # Relationships
    project = relationship("Project", back_populates="gen_jobs")

    __table_args__ = (
        CheckConstraint(
            "job_type IN ('code_generation', 'document_generation', 'test_generation', 'refactoring')",
            name="chk_gen_job_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed', 'cancelled')",
            name="chk_gen_job_status",
        ),
    )

