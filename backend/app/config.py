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

    # 数据库配置 - 强制使用持久化磁盘（Render）或本地路径
    # 忽略外部设置的 DATABASE_URL，因为代码自动检测了正确路径
    DATABASE_URL: str = _DB_URL

    @classmethod
    def settings_customise_sources(cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings):
        """自定义配置源顺序，确保 DATABASE_URL 不被环境变量覆盖"""
        # 过滤掉环境变量中的 DATABASE_URL（防止 Render Dashboard 错误配置覆盖）
        from pydantic_settings.sources import EnvSettingsSource
        
        class FilteredEnvSource(EnvSettingsSource):
            def prepare_field_value(self, field_name: str, field, value: str, value_is_complex: bool):
                if field_name.upper() == "DATABASE_URL":
                    return None, False, False  # 忽略环境变量中的 DATABASE_URL
                return super().prepare_field_value(field_name, field, value, value_is_complex)
        
        filtered_env = FilteredEnvSource(settings_cls)
        return init_settings, filtered_env, dotenv_settings, file_secret_settings

    # Redis 配置 (可选)
    REDIS_URL: str = ""

    # AI 服务 API Keys
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"  # 使用当前可用的模型
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
