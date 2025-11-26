"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.routes import router as v1_router
from app.core.config import settings
from app.core.cors import setup_cors
from app.core.exceptions import (
    AppError,
    app_exception_handler,
    database_exception_handler,
    general_exception_handler,
)
from app.core.logging import setup_logging

# 로깅 설정
setup_logging()

# FastAPI 앱 생성
app = FastAPI(
    title="Efficient AI Backend",
    description="AI 기반 효율적인 개발 백엔드 시스템",
    version="0.1.0",
    debug=settings.debug,
)

# CORS 설정
setup_cors(app)

# 예외 핸들러 등록
app.add_exception_handler(SQLAlchemyError, database_exception_handler)
app.add_exception_handler(AppError, app_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# API 라우터 등록
app.include_router(v1_router, prefix=settings.api_prefix)

# 개발 환경에서 인증 우회 (DEBUG 모드일 때만)
if settings.debug:
    from app.db.models import User
    from app.domain.auth import get_current_user

    def fake_user():
        # DB에서 첫 번째 사용자를 찾거나, 없으면 생성
        from app.db.database import SessionLocal

        db = SessionLocal()
        try:
            user = db.query(User).first()
            if not user:
                # 테스트용 사용자 생성
                user = User(
                    user_id="dev-user",
                    email="dev@example.com",
                    display_name="Dev User",
                    password_hash="",
                )
                db.add(user)
                db.commit()
                db.refresh(user)
            return user
        finally:
            db.close()

    app.dependency_overrides[get_current_user] = fake_user


@app.get("/", include_in_schema=False)
async def root():
    """루트 엔드포인트 - /docs로 리다이렉트"""
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["health"])
async def health_check():
    """헬스 체크 엔드포인트"""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "debug": settings.debug,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
