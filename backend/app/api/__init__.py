"""API 路由模块"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "ok", "message": "Paper Finder Agent is running"}
