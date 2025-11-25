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

import random
import string
from datetime import datetime
from typing import Any

from sqlalchemy import (  # type: ignore
    CLOB,
    TIMESTAMP,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
    func,
    select,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship  # type: ignore

from app.db.database import Base


class User(Base):
    __tablename__ = "users"
    user_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), default="")
    display_name: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.systimestamp(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.systimestamp(),  # INSERT 시 기본값
        onupdate=func.systimestamp(),  # UPDATE 시 자동 갱신
    )
    social_accounts: Mapped[list["SocialAccount"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class SocialAccount(Base):
    __tablename__ = "socialaccounts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(120), ForeignKey("users.user_id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String(120), nullable=False)
    provider_user_id: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    user: Mapped["User"] = relationship(back_populates="social_accounts")

    __table_args__ = (UniqueConstraint("provider", "provider_user_id", name="uq_social_provider_user"),)


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

    id: Mapped[int] = mapped_column(primary_key=True, comment="프로젝트 고유 ID")
    project_idx: Mapped[str] = mapped_column(nullable=False, comment="user별 프로젝트 idx")
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="프로젝트 제목")
    content_md: Mapped[str] = mapped_column(comment="프로젝트 내용")
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default=text("todo"), comment="프로젝트 상태")

    owner_id: Mapped[str] = mapped_column(String(120), comment="프로젝트 소유자")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("SYSTIMESTAMP"),
        nullable=False,
        comment="생성 시간",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,  # 기존 그대로 timezone 옵션 없이 유지
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="수정 시간",
    )

    # Relationships
    documents: Mapped[list["Document"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,  # DB에 ON DELETE CASCADE 있으면 이걸 켜면 추가 DELETE 안 날림
    )
    tasks: Mapped[list["Task"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    gen_jobs: Mapped[list["GenJob"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    mcp_connections: Mapped[list["MCPConnection"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    mcp_sessions: Mapped[list["MCPSession"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # Check constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('todo', 'in_progress', 'review', 'done')",
            name="ck_projects_status",
        ),
        UniqueConstraint(project_idx, name="uq_projects_project_idx"),
    )


def rand4() -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=4))


# INSERT 전에 자동으로 고유 project_idx 생성
@event.listens_for(Project, "before_insert")
def generate_project_idx(mapper, connection, target):
    if target.project_idx:  # 이미 값 있으면 스킵
        return

    while True:
        idx = rand4()
        stmt = select(Project.project_idx).where(Project.project_idx == idx).limit(1)

        exists = connection.execute(stmt).fetchone()

        if not exists:
            target.project_idx = idx
            break


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

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="문서 고유 ID",
    )

    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),  # FK + 삭제시 CASCADE
        nullable=False,
        comment="프로젝트 ID",
    )

    type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="문서 타입 (PRD, USER_STORY, SRS)",
    )

    title: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        comment="문서 제목",
    )

    content_md: Mapped[str | None] = mapped_column(
        CLOB,
        nullable=True,
        comment="Markdown 형식 내용",
    )

    author_id: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        comment="작성자 ID",
    )

    last_editor_id: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        comment="마지막 수정자 ID",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),  # Oracle의 DEFAULT SYSTIMESTAMP 대응
        nullable=False,
        comment="생성 시각",
    )

    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,  # DDL에서도 nullable
        onupdate=func.now(),  # UPDATE 시 자동 갱신
        comment="수정 시각",
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default=text("todo"), comment="문서 상태")

    # 테이블 제약 조건 및 인덱스
    __table_args__ = (
        CheckConstraint("type IN ('PRD','USER_STORY','SRS')", name="ck_documents_type"),
        CheckConstraint(
            "status IN ('todo', 'in_progress', 'review', 'done')",
            name="ck_documents_status",
        ),
        Index("ix_documents_project_type", "project_id", "type"),
    )

    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="documents",
    )


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="채팅 세션 고유 ID")

    file_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="파일 타입 (PROJECT, PRD, USER_STORY, SRS, TASK)")

    file_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="연결된 파일 ID")

    user_id: Mapped[str] = mapped_column(String(120), nullable=False, comment="세션 소유자 ID")

    created_at: Mapped[Any] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("SYSTIMESTAMP"),
        nullable=False,
        comment="세션 생성 시간",
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="메시지 고유 ID")

    session_id: Mapped[int] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        comment="연결된 채팅 세션 ID",
    )

    role: Mapped[str] = mapped_column(String(50), nullable=False, comment="메시지 주체 (user, assistant, system, tool)")

    user_id: Mapped[str] = mapped_column(String(120), nullable=True, comment="사용자 ID")

    content: Mapped[str | None] = mapped_column(Text, nullable=True, comment="메시지 내용 (텍스트)")

    tool_calls_json: Mapped[str | None] = mapped_column(Text, nullable=True, comment="AI tool 호출 정보(JSON 문자열)")

    created_at = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("SYSTIMESTAMP"),
        nullable=False,
        comment="메시지 생성 시각",
    )


class Task(Base):
    """태스크 모델

    프로젝트의 개발 태스크(기능, 버그, 기타)를 관리합니다.

    Attributes:
        id: 태스크 ID
        project_id: 프로젝트 외래키
        title: 태스크 제목
        description: 태스크 설명 (CLOB)
        description_md: 태스크 설명 마크다운 (CLOB)
        type: 태스크 타입 (VARCHAR2 + CHECK: 'feat', 'bug', 'docs', 'design', 'refactor')
        source: 태스크 생성 소스 (VARCHAR2 + CHECK: 'MCP', 'USER', 'AI')
        status: 태스크 상태 (VARCHAR2 + CHECK: 'todo', 'in_progress', 'review', 'done')
        priority: 우선순위 (INTEGER, 0-10)
        tags: 태그 목록 (CLOB, JSON 배열 문자열)
        due_at: 마감일 (TIMESTAMP)
        result_files: 생성/수정된 파일 목록 (CLOB, JSON 배열 문자열)
        summary: 작업 요약 (CLOB)
        duration: 작업 소요 시간 (초 단위, INTEGER)
        result_logs: 결과 로그 (CLOB, 마크다운 형식)
        created_at: 생성 시간
        updated_at: 수정 시간

    Relationships:
        - project: 소속 프로젝트
        - parent_links: 이 태스크를 부모로 하는 링크들
        - child_links: 이 태스크를 자식으로 하는 링크들
    """

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="태스크 ID",
    )
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        comment="프로젝트 외래키",
    )
    title: Mapped[str | None] = mapped_column(
        String(500),
        comment="태스크 제목",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        comment="태스크 설명 (CLOB)",
    )
    description_md: Mapped[str | None] = mapped_column(
        CLOB,
        comment="태스크 설명 마크다운 (CLOB)",
    )
    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="feat",
        comment="태스크 타입",
    )

    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="USER",
        comment="태스크 생성 소스",
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="todo",
        comment="태스크 상태",
    )

    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
        comment="우선순위 (0-10)",
    )
    tags: Mapped[str | None] = mapped_column(
        CLOB,
        comment="태그 목록 (JSON 배열 문자열)",
    )

    due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        comment="마감일",
    )

    result_files: Mapped[str | None] = mapped_column(
        CLOB,
        comment="생성/수정된 파일 목록 (JSON 배열 문자열)",
    )

    summary: Mapped[str | None] = mapped_column(
        CLOB,
        comment="작업 요약",
    )

    duration: Mapped[int | None] = mapped_column(
        Integer,
        comment="작업 소요 시간 (초 단위)",
    )

    result_logs: Mapped[str | None] = mapped_column(
        CLOB,
        comment="결과 로그 (마크다운 형식)",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="생성 시간",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="수정 시간",
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="tasks",
    )

    parent_links: Mapped[list["TaskLink"]] = relationship(
        "TaskLink",
        foreign_keys="TaskLink.parent_task_id",
        back_populates="parent_task",
    )

    child_links: Mapped[list["TaskLink"]] = relationship(
        "TaskLink",
        foreign_keys="TaskLink.child_task_id",
        back_populates="child_task",
    )

    # ------------------------------------------------------------------
    # Table Constraints
    # ------------------------------------------------------------------

    __table_args__ = (
        CheckConstraint(
            "status IN ('todo', 'in_progress', 'review', 'done')",
            name="chk_task_status",
        ),
        CheckConstraint(
            "type IN ('feat', 'bug', 'docs', 'design', 'refactor')",
            name="chk_task_type",
        ),
        CheckConstraint(
            "source IN ('MCP', 'USER', 'AI')",
            name="chk_task_source",
        ),
        CheckConstraint(
            "priority >= 0 AND priority <= 10",
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
        job_type: 작업 타입 (VARCHAR2 + CHECK:
         'code_generation', 'document_generation', 'test_generation')
        status: 작업 상태 (VARCHAR2 + CHECK:
         'pending', 'running', 'completed', 'failed', 'cancelled')
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
            "job_type IN (" "'code_generation', 'document_generation', 'test_generation', 'refactoring'" ")",
            name="chk_gen_job_type",
        ),
        CheckConstraint(
            "status IN (" "'pending', 'running', 'completed', 'failed', 'cancelled'" ")",
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
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        comment="세션 소속 프로젝트",
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
    project = relationship("Project", back_populates="mcp_sessions")
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
        status: 실행 상태 (VARCHAR2 + CHECK:
         'pending', 'running', 'completed', 'failed', 'cancelled')
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
    tool_name = Column("tool_id", String(255), comment="툴 이름")
    prompt_name = Column("prompt_name", String(255), comment="프롬프트 이름")
    mode = Column("run_mode", String(50), comment="실행 모드")
    status = Column(String(50), nullable=False, default="pending", comment="실행 상태")
    result = Column("result", Text, comment="실행 결과 (CLOB)")
    config = Column("config", Text, comment="실행 설정 (JSON)")
    arguments = Column("arguments", Text, comment="실행 인자 (JSON)")
    progress = Column("progress", String(10), comment="진행률 (0-1)")
    message = Column("message", String(500), comment="상태 메시지")
    created_at = Column("created_at", DateTime, nullable=False, default=datetime.utcnow, comment="생성 시간")
    updated_at = Column(
        "updated_at",
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
            "status IN (" "'pending', 'queued', 'running', 'succeeded', 'completed', 'failed', 'cancelled'" ")",
            name="chk_mcp_run_status",
        ),
    )
