from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str
    app_version: str
    environment: Literal["development", "staging", "production"]
    debug: bool = False
    database_url: str

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    sec_user_agent: str
    sec_base_url: str = "https://www.sec.gov"
    sec_data_base_url: str = "https://data.sec.gov"

    document_storage_path: str = "data"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()