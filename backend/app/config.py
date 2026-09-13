from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "个人投资助手"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # 数据库配置
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/invest_assistant"

    # 数据目录
    DATA_DIR: Path = Path(__file__).parent.parent / "data"
    CACHE_DIR: Path = Path(__file__).parent.parent / "data" / "cache"

    # API配置
    API_PREFIX: str = "/api"

    # Set the bootstrap values once to provision the first administrator.
    ACCESS_TOKEN_COOKIE_NAME: str = "invest_access"
    REFRESH_TOKEN_COOKIE_NAME: str = "invest_refresh"
    CSRF_COOKIE_NAME: str = "invest_csrf"
    ACCESS_TOKEN_MINUTES: int = 15
    REFRESH_TOKEN_DAYS: int = 14
    JWT_SECRET: str = ""
    JWT_ISSUER: str = "personal-invest-assistant"
    JWT_AUDIENCE: str = "personal-invest-assistant-web"
    SESSION_SECURE: bool = False
    CORS_ORIGINS: str = "http://localhost:3001,http://127.0.0.1:3001"
    CSRF_TRUSTED_ORIGINS: str = ""
    BOOTSTRAP_ADMIN_USERNAME: str = ""
    BOOTSTRAP_ADMIN_PASSWORD: str = ""

    # 开发环境可由应用自动迁移；生产环境由独立 migrate 容器执行。
    RUN_MIGRATIONS_ON_STARTUP: bool = True
    SCHEDULER_ENABLED: bool = True
    SCHEDULER_TIMEZONE: str = "Asia/Shanghai"

    # LLM 配置
    LLM_PROVIDER: str = "anthropic"  # anthropic / openai
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
    ANTHROPIC_BASE_URL: str = ""  # 留空用默认，代理时设置
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_BASE_URL: str = ""  # 留空用默认，代理/Azure时设置

    # Agent rollout: when disabled, retain the deterministic fixed-plan path.
    CONSTRAINED_AGENT_ENABLED: bool = True

    class Config:
        env_file = ".env"

settings = Settings()

# 确保目录存在
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.CACHE_DIR.mkdir(parents=True, exist_ok=True)
