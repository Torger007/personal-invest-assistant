from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "个人投资助手"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # 数据库配置
    DATABASE_URL: str = "sqlite:///./data/database.db"

    # 数据目录
    DATA_DIR: Path = Path(__file__).parent.parent / "data"
    CACHE_DIR: Path = Path(__file__).parent.parent / "data" / "cache"

    # API配置
    API_PREFIX: str = "/api"

    # LLM 配置
    LLM_PROVIDER: str = "anthropic"  # anthropic / openai
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
    ANTHROPIC_BASE_URL: str = ""  # 留空用默认，代理时设置
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_BASE_URL: str = ""  # 留空用默认，代理/Azure时设置

    class Config:
        env_file = ".env"

settings = Settings()

# 确保目录存在
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.CACHE_DIR.mkdir(parents=True, exist_ok=True)
