"""SQLAlchemy models for database.

이 파일에는 데이터베이스에 생성될 모든 테이블의 모델이 정의되어 있습니다.

설계 특징 (Oracle/SQLite 호환):
1. ENUM 대신 VARCHAR + CHECK 제약조건 사용 (양쪽 모두 지원)
2. 긴 텍스트는 Text 타입 사용 (Oracle: CLOB, SQLite: TEXT)
3. PK는 autoincrement 사용 (Oracle: IDENTITY, SQLite: AUTOINCREMENT)
4. 타임스탬프는 DateTime 사용

주의사항:
- 로컬 개발 시 SQLite 사용 권장 (sqlite:///./local.db)
- 프로덕션에서는 Oracle 사용 (oracle+oracledb://...)
- 모델은 양쪽 데이터베이스 모두 호환되도록 설계됨
"""

from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    CheckConstraint,
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
    mcp_connections = relationship("MCPConnection", back_populates="project")

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
        title: 문서 제목
        content: 문서 내용 (CLOB - 긴 텍스트 저장)
        doc_type: 문서 타입 (VARCHAR2 + CHECK: 'PRD', 'UserStory', 'SRS')
        created_at: 생성 시간
        updated_at: 수정 시간
    
    Relationships:
        - project: 소속 프로젝트
        - versions: 문서의 버전들
    """

    __tablename__ = "documents"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="문서 고유 ID",
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
        comment="문서 제목",
    )
    content = Column(
        Text,
        comment="문서 내용 (CLOB)",
    )
    doc_type = Column(
        String(50),
        nullable=False,
        comment="문서 타입",
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
    project = relationship("Project", back_populates="documents")
    versions = relationship("DocumentVersion", back_populates="document")

    __table_args__ = (
        CheckConstraint(
            "doc_type IN ('PRD', 'UserStory', 'SRS')",
            name="chk_document_type",
        ),
    )


class DocumentVersion(Base):
    """문서 버전 모델
    
    문서의 변경 이력을 버전별로 관리합니다.
    
    Attributes:
        id: 버전 ID
        document_id: 문서 외래키
        version_number: 버전 번호 (정수)
        content: 해당 버전의 내용 (CLOB)
        created_at: 버전 생성 시간
    
    설명:
        - 문서가 수정될 때마다 새 버전이 생성됨
        - 버전 번호는 순차적으로 증가 (1, 2, 3, ...)
        - 이전 버전의 내용은 항상 복구 가능
    """

    __tablename__ = "document_versions"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="버전 ID",
    )
    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        comment="문서 외래키",
    )
    version_number = Column(
        Integer,
        nullable=False,
        comment="버전 번호",
    )
    content = Column(
        Text,
        nullable=False,
        comment="버전별 문서 내용 (CLOB)",
    )
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="버전 생성 시간",
    )

    # Relationships
    document = relationship("Document", back_populates="versions")


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


class MCPConnection(Base):
    """MCP 연결 모델
    
    MCP (Model Context Protocol) 연결 정보를 저장합니다.
    
    Attributes:
        id: 연결 고유 ID
        project_id: 프로젝트 외래키
        connection_type: 연결 타입 (VARCHAR2 + CHECK: 'cursor', 'claude', 'chatgpt')
        status: 연결 상태 (VARCHAR2 + CHECK: 'active', 'inactive', 'error')
        created_at: 생성 시간
        updated_at: 수정 시간
    
    Relationships:
        - project: 소속 프로젝트
        - sessions: 이 연결의 세션들
    """

    __tablename__ = "mcp_connections"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="연결 고유 ID",
    )
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        comment="프로젝트 외래키",
    )
    connection_type = Column(
        String(50),
        nullable=False,
        comment="연결 타입",
    )
    status = Column(
        String(50),
        nullable=False,
        default="active",
        comment="연결 상태",
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
    project = relationship("Project", back_populates="mcp_connections")
    sessions = relationship("MCPSession", back_populates="connection")

    __table_args__ = (
        CheckConstraint(
            "connection_type IN ('cursor', 'claude', 'chatgpt')",
            name="chk_mcp_connection_type",
        ),
        CheckConstraint(
            "status IN ('active', 'inactive', 'error')",
            name="chk_mcp_connection_status",
        ),
    )


class MCPSession(Base):
    """MCP 세션 모델
    
    MCP 세션 정보를 저장합니다.
    
    Attributes:
        id: 세션 고유 ID
        connection_id: 연결 외래키
        status: 세션 상태 (VARCHAR2 + CHECK: 'active', 'closed', 'error')
        context: 세션 컨텍스트 (JSON 형태로 저장, Text 타입)
        created_at: 생성 시간
        updated_at: 수정 시간
    
    Relationships:
        - connection: 소속 연결
        - runs: 이 세션의 실행들
    """

    __tablename__ = "mcp_sessions"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="세션 고유 ID",
    )
    connection_id = Column(
        Integer,
        ForeignKey("mcp_connections.id", ondelete="CASCADE"),
        nullable=False,
        comment="연결 외래키",
    )
    status = Column(
        String(50),
        nullable=False,
        default="active",
        comment="세션 상태",
    )
    context = Column(
        Text,
        comment="세션 컨텍스트 (JSON)",
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
    connection = relationship("MCPConnection", back_populates="sessions")
    runs = relationship("MCPRun", back_populates="session")

    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'closed', 'error')",
            name="chk_mcp_session_status",
        ),
    )


class MCPRun(Base):
    """MCP 실행 모델
    
    MCP 툴/프롬프트 실행 정보를 저장합니다.
    
    Attributes:
        id: 실행 고유 ID
        session_id: 세션 외래키
        tool_name: 툴 이름 (선택적)
        prompt_name: 프롬프트 이름 (선택적)
        status: 실행 상태 (VARCHAR2 + CHECK: 'pending', 'running', 'completed', 'failed', 'cancelled')
        result: 실행 결과 (CLOB)
        arguments: 실행 인자 (JSON 형태로 저장, Text 타입)
        progress: 진행률 (0-1, String)
        message: 상태 메시지
        created_at: 생성 시간
        updated_at: 수정 시간
    
    Relationships:
        - session: 소속 세션
    """

    __tablename__ = "mcp_runs"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="실행 고유 ID",
    )
    session_id = Column(
        Integer,
        ForeignKey("mcp_sessions.id", ondelete="CASCADE"),
        nullable=False,
        comment="세션 외래키",
    )
    tool_name = Column(
        String(255),
        comment="툴 이름",
    )
    prompt_name = Column(
        String(255),
        comment="프롬프트 이름",
    )
    status = Column(
        String(50),
        nullable=False,
        default="pending",
        comment="실행 상태",
    )
    result = Column(
        Text,
        comment="실행 결과 (CLOB)",
    )
    arguments = Column(
        Text,
        comment="실행 인자 (JSON)",
    )
    progress = Column(
        String(10),
        comment="진행률 (0-1)",
    )
    message = Column(
        String(500),
        comment="상태 메시지",
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
    session = relationship("MCPSession", back_populates="runs")

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed', 'cancelled')",
            name="chk_mcp_run_status",
        ),
    )

