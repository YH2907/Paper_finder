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

# Render persistent disk path (production) or local path (development)
RENDER_DATA_DIR = Path("/app/data")
if IS_RENDER or RENDER_DATA_DIR.exists():
    # Running on Render - use persistent disk
    RENDER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    _DB_PATH = RENDER_DATA_DIR / "paperfinder.db"
else:
    # Running locally
    _DB_PATH = BACKEND_DIR / "paperfinder.db"

# 确保数据库文件路径的 SQLite URL 使用绝对路径（4个斜杠）
_DB_URL = f"sqlite:///{_DB_PATH.as_posix()}"


# 已知可用的 Groq 模型
VALID_GROQ_MODELS = {
    "groq/compound",
    "groq/compound-mini",
    "qwen/qwen3.8-27b",
    "qwen/qwen3.6-27b",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "allam-2-7b",
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

    # 数据库配置
    DATABASE_URL: str = _DB_URL

    # Redis 配置 (可选)
    REDIS_URL: str = ""

    # AI 服务 API Keys
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "groq/compound"
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
        return bool(self.GROQ_API_KEY or self.GEMINI_API_KEY)
    
    def get_groq_model(self) -> str:
        """获取有效的 Groq 模型名称（自动纠正无效模型）"""
        if self.GROQ_MODEL and self.GROQ_MODEL in VALID_GROQ_MODELS:
            return self.GROQ_MODEL
        # 无效模型，返回默认值
        return "groq/compound"


# 全局单例
settings = Settings()
