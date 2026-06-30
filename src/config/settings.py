"""Application configuration using Pydantic Settings."""

import os
from functools import lru_cache
from pathlib import Path
from typing import ClassVar, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # LLM Configuration (OpenAI-compatible API)
    llm_api_key: str = Field(default="", description="LLM API key for OpenAI-compatible endpoint")
    llm_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="LLM API base URL (OpenAI-compatible)"
    )
    model: str = Field(default="glm-5", description="LLM model identifier (GLM-5)")

    # Database Configuration
    db_host: str = Field(default="localhost", description="Database host")
    db_port: int = Field(default=3306, description="Database port")
    db_user: str = Field(default="medical_user", description="Database username")
    db_password: str = Field(default="", description="Database password")
    db_name: str = Field(default="medical_agent", description="Database name")

    @property
    def database_url(self) -> str:
        """Construct SQLAlchemy database URL."""
        return f"mysql+aiomysql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    # Memory Configuration (Mem0)
    mem0_api_key: str = Field(default="", description="Mem0 API key for memory management")
    vector_store_type: Literal["mem0", "chroma", "faiss"] = Field(
        default="mem0",
        description="Vector store implementation type"
    )

    # Redis Configuration
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_password: str = Field(default="", description="Redis password")
    redis_db: int = Field(default=0, description="Redis database number")

    @property
    def redis_url(self) -> str:
        """Construct Redis URL."""
        return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # Application Configuration
    app_name: str = Field(default="Medical Agent", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    debug: bool = Field(default=True, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is a valid logging level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.upper()

    # CORS Configuration
    cors_origins: list[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:3002",
            "http://localhost:8000",
            "*",
        ],
        description="Allowed CORS origins"
    )

    # JWT Configuration (for future authentication)
    jwt_secret_key: str = Field(default="", description="JWT secret key")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiration_minutes: int = Field(default=60 * 24, description="JWT token expiration in minutes")

    # Skill Executor Configuration
    skill_executor_backend: Literal["subprocess", "msagent-sandbox", "auto"] = Field(
        default="subprocess",
        description="Skill execution backend: subprocess, msagent-sandbox, or auto"
    )
    skill_executor_timeout: int = Field(default=30, description="Skill execution timeout in seconds")
    skill_executor_docker_image: str = Field(default="python:3.11-slim", description="Docker image for msagent-sandbox")

    # External API Integration
    external_api_enabled: bool = Field(default=True, description="Enable external API push (sync patient data + insight)")
    external_api_use_human_query: bool = Field(default=True, description="Use humanQuery API instead of legacy queryHealthData")

    # Path Configuration (supports NAS mount)
    _project_root: ClassVar[str] = str(Path(__file__).parent.parent.parent)
    skills_dir: str = Field(
        default=_project_root + "/skills",
        description="Skills directory path (env: SKILLS_DIR)"
    )
    data_dir: str = Field(
        default=_project_root + "/data",
        description="Data directory path (env: DATA_DIR)"
    )
    config_dir: str = Field(
        default=_project_root + "/config",
        description="Config directory path (env: CONFIG_DIR)"
    )
    wiki_dir: str = Field(
        default=_project_root + "/data/wiki",
        description="Wiki knowledge base directory (env: WIKI_DIR)"
    )
    wiki_upload_dir: str = Field(
        default=_project_root + "/data/wiki/_uploads",
        description="Temporary PDF upload directory (env: WIKI_UPLOAD_DIR)"
    )
    wiki_llm_model: str = Field(
        default="",
        description="LLM model for Wiki extraction (env: WIKI_LLM_MODEL). Falls back to 'model' if empty."
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

# Module-level singleton for convenient access
settings = get_settings()
