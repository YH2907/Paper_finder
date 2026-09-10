"""应用配置模块

使用 pydantic-settings 从环境变量加载配置。
"""
import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BACKEND_DIR / ".env"

# 检测是否在 Render 环境运行
IS_RENDER = os.environ.get("RENDER", "").lower() == "true" or os.environ.get("RENDER_SERVICE_ID", "") != ""


# 已知可用的 Groq 模型（按速度排序，推荐快速模型）
VALID_GROQ_MODELS = {
    "llama-3.3-70b-versatile",  # 快且强，推荐
    "llama-3.1-70b-versatile",
    "llama-3.1-8b-instant",     # 最快
    "gemma2-9b-it",
    "mixtral-8x7b-32768",
    "groq/compound-mini",
}


class Settings(BaseSettings):
    """应用全局配置"""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # 应用基本配置
    APP_NAME: str = "Paper Finder Agent"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    DEBUG: bool = True
    APP_TIMEZONE: str = "Asia/Shanghai"

    # Supabase 配置
    SUPABASE_URL: str = ""
    SUPABASE_PUBLISHABLE_KEY: str = ""
    SUPABASE_SECRET_KEY: str = ""
    SUPABASE_JWKS_URL: str = ""

    # Redis 配置 (可选)
    REDIS_URL: str = ""

    # AI 服务 API Keys
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"  # 更快的模型
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    # 学术数据源 API Keys（可选）
    IEEE_API_KEY: str = ""
    SEMANTIC_SCHOLAR_API_KEY: str = ""

    # JWT 配置
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    JWT_SECRET_KEY: str = "dev-jwt-secret-key"
    ALGORITHM: str = "HS256"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS 配置
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        """将 CORS_ORIGINS 字符串转换为列表"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def has_ai_configured(self) -> bool:
        """检查是否配置了 AI 服务的 API Key"""
        return bool(self.GROQ_API_KEY and self.GROQ_API_KEY.strip())
    
    def get_groq_model(self) -> str:
        """获取有效的 Groq 模型名称（自动纠正无效模型）"""
        if self.GROQ_MODEL and self.GROQ_MODEL in VALID_GROQ_MODELS:
            return self.GROQ_MODEL
        # 默认使用更快的模型
        return "llama-3.3-70b-versatile"
    
# 全局单例
settings = Settings()
