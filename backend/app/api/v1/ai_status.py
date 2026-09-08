"""AI 状态检查"""
from fastapi import APIRouter
from app.config import settings
from app.schemas.common import ResponseBase

router = APIRouter(prefix="/ai", tags=["AI"])


@router.get("/status", response_model=ResponseBase)
def get_ai_status():
    """检查 AI 配置状态（无需登录）"""
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



