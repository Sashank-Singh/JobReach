from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _discover_env_files() -> tuple[Path, ...]:
    """Monorepo root .env for local dev; cwd .env for Docker/Coolify."""
    candidates: list[Path] = []
    cwd_env = Path(".env")
    if cwd_env.exists():
        candidates.append(cwd_env)

    core = Path(__file__).resolve()
    if len(core.parents) > 4:
        repo_env = core.parents[4] / ".env"
        if repo_env.exists() and repo_env not in candidates:
            candidates.insert(0, repo_env)

    return tuple(candidates) if candidates else (Path(".env"),)


_ENV_FILES = _discover_env_files()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[str(p) for p in _ENV_FILES if p.exists()] or ".env",
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://jobreach:jobreach@localhost:5432/jobreach"
    database_url_sync: str = "postgresql://jobreach:jobreach@localhost:5432/jobreach"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: str = "http://localhost:3000"
    fireworks_api_key: str = ""
    fireworks_embedding_model: str = "accounts/fireworks/models/qwen3-embedding-8b"
    fireworks_chat_model: str = "accounts/fireworks/models/minimax-m3"
    job_collector_interval_hours: int = 1
    embedding_model: str = "accounts/fireworks/models/qwen3-embedding-8b"
    embedding_dimensions: int = 768
    jwt_secret: str = "change-me-in-production-jobreach-secret-key"
    jwt_expire_days: int = 30

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
