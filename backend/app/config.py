"""应用配置模块

使用 pydantic-settings 从环境变量加载配置。
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BACKEND_DIR / ".env"
DEFAULT_SQLITE_DB_PATH = BACKEND_DIR / "paperfinder.db"


class Settings(BaseSettings):
    """应用全局配置"""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # 忽略额外的环境变量
    )

    # 应用基本配置
    APP_NAME: str = "Paper Finder Agent"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    DEBUG: bool = True
    APP_TIMEZONE: str = "Asia/Shanghai"

    # 数据库配置
    DATABASE_URL: str = f"sqlite:///{DEFAULT_SQLITE_DB_PATH.as_posix()}"

    # Redis 配置 (可选)
    REDIS_URL: str = ""

    # AI 服务 API Keys
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama3-70b-8192"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # 学术数据源 API Keys（可选）
    IEEE_API_KEY: str = ""  # IEEE Xplore API Key（可选，无则使用网页搜索）
    SEMANTIC_SCHOLAR_API_KEY: str = ""  # Semantic Scholar API Key（可选）

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
        """检查是否配置了 AI 服务的 API Key

        Returns:
            只要配置了任意一个 AI 服务的 API Key 就返回 True
        """
        return bool(self.GROQ_API_KEY or self.GEMINI_API_KEY)


# 全局单例
settings = Settings()
