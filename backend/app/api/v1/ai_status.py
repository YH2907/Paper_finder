"""AI 状态检查"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.deps import get_current_user
from app.models.user import User
from app.schemas.common import ResponseBase
from app.config import settings
from app.services.ai.router import AIRouter
from app.services.ai.groq import GroqService
from app.services.ai.gemini import GeminiService
from app.services.ai.mock import MockAIService

router = APIRouter(prefix="/ai", tags=["AI"])


def _build_ai_router() -> AIRouter:
    """构建 AI 路由器"""
    if settings.has_ai_configured:
        primary = GroqService(api_key=settings.GROQ_API_KEY, model=settings.GROQ_MODEL)
        fallback = GeminiService(api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_MODEL)
    else:
        primary = MockAIService()
        fallback = MockAIService()
    return AIRouter(primary=primary, fallback=fallback)


@router.get("/status", response_model=ResponseBase)
def get_ai_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """检查 AI 配置状态"""
    has_groq = bool(settings.GROQ_API_KEY and settings.GROQ_API_KEY.strip())
    has_gemini = bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip())
    has_ai = has_groq or has_gemini
    
    return ResponseBase(
        success=True,
        message="AI 状态查询成功",
        data={
            "ai_configured": has_ai,
            "groq_configured": has_groq,
            "gemini_configured": has_gemini,
            "groq_model": settings.GROQ_MODEL if has_groq else None,
            "gemini_model": settings.GEMINI_MODEL if has_gemini else None,
        }
    )


@router.post("/test", response_model=ResponseBase)
async def test_ai(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """测试 AI 连接"""
    if not settings.has_ai_configured:
        return ResponseBase(
            success=False,
            message="未配置任何 AI API Key",
            data=None
        )
    
    ai_router = _build_ai_router()
    try:
        messages = [{"role": "user", "content": "Say 'AI test successful' in one sentence."}]
        response = await ai_router.chat(messages)
        return ResponseBase(
            success=True,
            message="AI 测试成功",
            data={"response": response}
        )
    except Exception as e:
        return ResponseBase(
            success=False,
            message=f"AI 测试失败: {str(e)}",
            data=None
        )
