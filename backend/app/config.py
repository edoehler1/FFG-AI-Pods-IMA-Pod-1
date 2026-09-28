import os
from pathlib import Path

from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_ROOT / "data" / "signals.db"


class Settings(BaseSettings):
    database_url: str = f"sqlite:///{DB_PATH}"
    anthropic_api_key: str = ""
    anthropic_base_url: str = ""
    anthropic_model: str = "bedrock.anthropic.claude-sonnet-4-6"
    news_api_key: str = ""
    app_env: str = "development"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    model_config = {"env_file": str(PROJECT_ROOT / ".env"), "env_file_encoding": "utf-8"}


settings = Settings()
