from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://jobreach:jobreach@localhost:5432/jobreach"
    database_url_sync: str = "postgresql://jobreach:jobreach@localhost:5432/jobreach"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: str = "http://localhost:3000"
    openai_api_key: str = ""
    job_collector_interval_hours: int = 1
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
