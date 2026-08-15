from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str
    app_version: str
    environment: Literal["development", "staging", "production"]
    debug: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()