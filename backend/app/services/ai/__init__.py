# AI 服务模块

from .base import BaseAIService
from .mock import MockAIService
from .router import AIRouter
from .analyzer import PaperAnalyzer
from .chat import ChatSession, ChatService as AIChatService


# Singleton AI router — avoid creating new httpx clients per request
_ai_router: AIRouter | None = None


def build_ai_router():
    """统一构建 AI 路由器（单例，复用 httpx client）
    
    - Groq：唯一 AI 提供商
    """
    global _ai_router
    if _ai_router is not None:
        return _ai_router

    from app.config import settings
    from .groq import GroqService

    if not settings.GROQ_API_KEY or not settings.GROQ_API_KEY.strip():
        raise RuntimeError("GROQ_API_KEY is required")

    groq = GroqService(api_key=settings.GROQ_API_KEY, model=settings.get_groq_model())
    _ai_router = AIRouter(primary=groq)
    return _ai_router


__all__ = [
    "BaseAIService",
    "MockAIService",
    "AIRouter",
    "PaperAnalyzer",
    "ChatSession",
    "AIChatService",
    "build_ai_router",
]
