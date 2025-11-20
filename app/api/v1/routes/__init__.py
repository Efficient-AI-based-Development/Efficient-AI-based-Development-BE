"""API v1 route modules."""

from fastapi import APIRouter

from app.api.v1.routes import ai, auth, chats, documents, generate, insights, mcp, projects, tasks

router = APIRouter()

# 라우터 등록
router.include_router(projects.router)
router.include_router(documents.router)
router.include_router(generate.router)
router.include_router(tasks.router)
router.include_router(insights.router)
router.include_router(mcp.router)
router.include_router(chats.router)
router.include_router(auth.router)
router.include_router(ai.router)
