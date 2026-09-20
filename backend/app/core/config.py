from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AgentGrid"
    app_version: str = "0.1.0"
    app_environment: str = "development"

    api_host: str = "127.0.0.1"
    api_port: int = 8000

    log_level: str = "INFO"
    database_url: str = ""

    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()