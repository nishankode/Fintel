from pydantic import field_validator
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

    document_storage_provider: Literal["local", "s3"] = "local"
    document_storage_path: str = "data"
    s3_bucket_name: str | None = None
    s3_key_prefix: str = ""
    s3_endpoint_url: str | None = None
    s3_region_name: str | None = None

    embedding_model_name: str = "BAAI/bge-small-en-v1.5"
    embedding_dimension: int = 384
    embedding_device: str = "cpu"

    redis_url: str = "redis://localhost:6379/0"
    ingestion_queue_name: str = "fintel:ingestion_jobs"

    llm_provider: Literal["extractive", "openai"] = "extractive"
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-5-mini"
    openai_timeout_seconds: float = 30.0

    rate_limit_enabled: bool = True
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(
        cls,
        value,
    ):
        if isinstance(value, str):
            normalized = value.strip().lower()

            if normalized in {
                "release",
                "prod",
                "production",
            }:
                return False

        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
