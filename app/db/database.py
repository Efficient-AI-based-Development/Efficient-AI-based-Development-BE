"""Database connection and session management."""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

# Oracle-specific engine configuration
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # 연결 전 유효성 검사
    pool_size=5,  # 연결 풀 크기
    max_overflow=10,  # 추가 연결 허용
    echo=settings.debug,  # 디버그 모드에서 SQL 쿼리 출력
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Base class for models
Base = declarative_base()


def get_db():
    """데이터베이스 세션 의존성 함수
    
    FastAPI의 Depends와 함께 사용하여 각 요청마다 DB 세션을 제공합니다.
    요청 종료 시 자동으로 세션이 닫힙니다.
    
    사용 예시:
        @router.get("/projects")
        def get_projects(db: Session = Depends(get_db)):
            return db.query(Project).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

