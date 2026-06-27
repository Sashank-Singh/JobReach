from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root .env (local dev without Docker) + cwd .env (Coolify / docker)
_REPO_ROOT = Path(__file__).resolve().parents[4]
_ENV_FILES = (
    _REPO_ROOT / ".env",
    Path(".env"),
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[str(p) for p in _ENV_FILES if p.exists()] or ".env",
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://jobreach:jobreach@localhost:5432/jobreach"
    database_url_sync: str = "postgresql://jobreach:jobreach@localhost:5432/jobreach"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: str = "http://localhost:3000"
    gemini_api_key: str = ""
    gemini_embedding_model: str = "text-embedding-004"
    gemini_chat_model: str = "gemini-2.0-flash"
    job_collector_interval_hours: int = 1
    embedding_model: str = "text-embedding-004"
    embedding_dimensions: int = 768
    jwt_secret: str = "change-me-in-production-jobreach-secret-key"
    jwt_expire_days: int = 30

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
