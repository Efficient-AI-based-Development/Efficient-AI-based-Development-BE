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
from sqlalchemy import (  # type: ignore
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,

    CheckConstraint, text, CLOB, func, UniqueConstraint, Index, TIMESTAMP,
)
from sqlalchemy.orm import relationship  # type: ignore

from app.db.database import Base


class Project(Base):
    """프로젝트 모델
    
    AI 개발 프로젝트의 기본 정보를 저장합니다.
    
    Attributes:
        id: 프로젝트 고유 ID
        project_idx: user 별 프로젝트 idx
        title: 프로젝트 제목 (VARCHAR2)
        content_md: 내용
        status: 프로젝트 상태 (VARCHAR2 + CHECK: 'not_started','in_progress','completed')
        owner_id: 프로젝트 소유자
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
        comment="프로젝트 고유 ID",
    )
    project_idx = Column(
        Integer,
        nullable=False,
        comment="user별 프로젝트 idx"
    )
    title = Column(
        String(200),
        nullable=False,
        comment="프로젝트 제목",
    )
    content_md = Column(
        String,
        comment="프로젝트 내용",
    )
    status = Column(
        String(30),
        nullable=False,
        server_default=text("'in_progress'"),
        comment="프로젝트 상태",
    )
    owner_id = Column(
        String(120),
        comment="프로젝트 소유자"
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=text("SYSTIMESTAMP"),
        nullable=False,
        comment="생성 시간"
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="수정 시간",
    )

    # Relationships
    documents = relationship(
        "Document",
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,  # DB에 ON DELETE CASCADE 있으면 이걸 켜면 추가 DELETE 안 날림
    )
    tasks = relationship(
        "Task",
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    gen_jobs = relationship(
        "GenJob",
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    mcp_connections = relationship(
        "MCPConnection",
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # Check constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('not_started','in_progress','completed')",
            name='ck_projects_status'
        ),
    )


class Document(Base):
    """문서 모델
    
    프로젝트의 문서(PRD, User_Story, SRS 등)를 저장합니다.
    
    Attributes:
        id: 문서 고유 ID
        project_id: 프로젝트 외래키
        type: 문서 타입 (VARCHAR2 + CHECK: 'PRD', 'USER_STORY', 'SRS')
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
            "type IN ('PRD','USER_STORY','SRS')",
            name='ck_documents_type'
        ),
        Index('ix_documents_project_type', 'project_id', 'type'),
    )

    project = relationship(
        "Project",
        back_populates="documents",
    )

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(
        Integer,
        primary_key=True,
        comment="채팅 세션 고유 ID"
    )

    file_type = Column(
        String(20),
        nullable=False,
        comment="파일 타입 (PROJECT, PRD, USER_STORY, SRS, TASK)"
    )

    file_id = Column(
        Integer,
        nullable=False,
        comment="연결된 파일 ID"
    )

    user_id = Column(
        String(120),
        nullable=False,
        comment="세션 소유자 ID"
    )

    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=text("SYSTIMESTAMP"),
        nullable=False,
        comment="세션 생성 시간"
    )

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="메시지 고유 ID"
    )

    session_id = Column(
        Integer,
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        comment="연결된 채팅 세션 ID"
    )

    role = Column(
        String(50),
        nullable=False,
        comment="메시지 주체 (user, assistant, system, tool)"
    )

    user_id = Column(
        String(120),
        nullable=True,
        comment="사용자 ID"
    )

    content = Column(
        CLOB,
        nullable=True,
        comment="메시지 내용 (텍스트)"
    )

    tool_calls_json = Column(
        CLOB,
        nullable=True,
        comment="AI tool 호출 정보(JSON 문자열)"
    )

    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=text("SYSTIMESTAMP"),
        nullable=False,
        comment="메시지 생성 시각"
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
        default="pending",
        comment="연결 상태",
    )
    config = Column(
        Text,
        comment="연결 설정 (JSON)",
    )
    env = Column(
        Text,
        comment="연결 환경 변수 (JSON)",
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
            "status IN ('pending', 'active', 'inactive', 'error')",
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
        default="ready",
        comment="세션 상태",
    )
    context = Column(
        Text,
        comment="세션 컨텍스트 (JSON)",
    )
    metadata_json = Column(
        "metadata",
        Text,
        comment="세션 메타데이터 (JSON)",
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
            "status IN ('ready', 'active', 'closed', 'error')",
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
    mode = Column(
        String(50),
        comment="실행 모드",
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
    config = Column(
        Text,
        comment="실행 설정 (JSON)",
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

