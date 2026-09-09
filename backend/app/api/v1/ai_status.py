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
            "groq_model": settings.get_groq_model() if has_groq else None,
            "gemini_model": settings.GEMINI_MODEL if has_gemini else None,
        }
    )


@router.get("/debug")
def get_debug_info():
    """调试端点：显示完整的配置信息"""
    return {
        "GROQ_API_KEY_set": bool(settings.GROQ_API_KEY and settings.GROQ_API_KEY.strip()),
        "GROQ_MODEL": settings.GROQ_MODEL,
        "GEMINI_API_KEY_set": bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip()),
        "GEMINI_MODEL": settings.GEMINI_MODEL,
        "DATABASE_URL": settings.DATABASE_URL,
        "APP_ENV": settings.APP_ENV,
        "version": "v2-model-validator",
    }



