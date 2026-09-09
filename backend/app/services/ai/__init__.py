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
    
    - Groq + Gemini：Groq 为主，Gemini 为备
    - 仅 Groq：Groq 为主，Mock 为备
    - 仅 Gemini：Mock 为主，Gemini 为备
    - 都没有：Mock 为主，Mock 为备
    """
    global _ai_router
    if _ai_router is not None:
        return _ai_router

    from app.config import settings
    from .groq import GroqService
    from .gemini import GeminiService

    has_groq = bool(settings.GROQ_API_KEY and settings.GROQ_API_KEY.strip())
    has_gemini = bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip())

    if has_groq and has_gemini:
        print(f"[AI Router] Groq({settings.get_groq_model()}) + Gemini")
        primary = GroqService(api_key=settings.GROQ_API_KEY, model=settings.get_groq_model())
        fallback = GeminiService(api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_MODEL)
    elif has_groq:
        print(f"[AI Router] Groq only ({settings.get_groq_model()})")
        primary = GroqService(api_key=settings.GROQ_API_KEY, model=settings.get_groq_model())
        fallback = MockAIService()
    elif has_gemini:
        print(f"[AI Router] Gemini only ({settings.GEMINI_MODEL})")
        primary = MockAIService()
        fallback = GeminiService(api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_MODEL)
    else:
        print("[AI Router] Mock only")
        primary = MockAIService()
        fallback = MockAIService()

    _ai_router = AIRouter(primary=primary, fallback=fallback)
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
