"""API 路由汇总"""
from fastapi import APIRouter
from app.api.v1 import auth, topics, papers, chat, notifications, users, settings, deep_research, ai_status

api_router = APIRouter()

# 注册各模块路由
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(topics.router)
api_router.include_router(papers.router)
api_router.include_router(chat.router)
api_router.include_router(notifications.router)
api_router.include_router(settings.router)
api_router.include_router(deep_research.router)
api_router.include_router(ai_status.router)


@api_router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "message": "Paper Finder API is running"}
