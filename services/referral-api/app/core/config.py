from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[4]
_ENV_FILES = (_REPO_ROOT / ".env", Path(".env"))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[str(p) for p in _ENV_FILES if p.exists()] or ".env",
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://jobreach:jobreach@localhost:5432/jobreach"
    cors_origins: str = "http://localhost:3000"
    job_api_url: str = "http://localhost:8000"
    jwt_secret: str = "change-me-in-production-jobreach-secret-key"
    daily_linkedin_send_limit: int = 20

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
