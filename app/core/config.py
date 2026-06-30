from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Support Ticket Resolution Platform"
    environment: str = "development"
    api_key: str = "dev-api-key"
    database_url: str | None = None
    database_path: str = "data/support_tickets.db"
    knowledge_base_path: str = "knowledge_base"
    use_llm: bool = False
    openai_api_key: str | None = None
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: int = 20
    llm_max_retries: int = 2

    @property
    def effective_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"sqlite:///{self.database_path}"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
