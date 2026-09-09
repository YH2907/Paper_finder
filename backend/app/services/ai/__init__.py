# AI 服务模块

from .base import BaseAIService
from .mock import MockAIService
from .router import AIRouter
from .analyzer import PaperAnalyzer
from .chat import ChatSession, ChatService as AIChatService


def build_ai_router():
    """统一构建 AI 路由器
    
    - Groq + Gemini：Groq 为主，Gemini 为备
    - 仅 Groq：Groq 为主，Mock 为备
    - 仅 Gemini：Mock 为主，Gemini 为备
    - 都没有：Mock 为主，Mock 为备
    """
    from app.config import settings
    from .groq import GroqService
    from .gemini import GeminiService

    has_groq = bool(settings.GROQ_API_KEY and settings.GROQ_API_KEY.strip())
    has_gemini = bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip())

    if has_groq and has_gemini:
        print(f"[AI Router] Groq({settings.GROQ_MODEL}) + Gemini")
        primary = GroqService(api_key=settings.GROQ_API_KEY, model=settings.GROQ_MODEL)
        fallback = GeminiService(api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_MODEL)
    elif has_groq:
        print(f"[AI Router] Groq only ({settings.GROQ_MODEL})")
        primary = GroqService(api_key=settings.GROQ_API_KEY, model=settings.GROQ_MODEL)
        fallback = MockAIService()
    elif has_gemini:
        print(f"[AI Router] Gemini only ({settings.GEMINI_MODEL})")
        primary = MockAIService()
        fallback = GeminiService(api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_MODEL)
    else:
        print("[AI Router] Mock only")
        primary = MockAIService()
        fallback = MockAIService()

    return AIRouter(primary=primary, fallback=fallback)


__all__ = [
    "BaseAIService",
    "MockAIService",
    "AIRouter",
    "PaperAnalyzer",
    "ChatSession",
    "AIChatService",
    "build_ai_router",
]
