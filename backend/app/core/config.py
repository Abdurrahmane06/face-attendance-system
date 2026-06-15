"""Application configuration using pydantic-settings.

Loads environment variables from .env file and provides typed access
to all configuration parameters.
"""

import os
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

# Look for .env in the project root (two levels up from this file)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env" if (_PROJECT_ROOT / ".env").exists() else ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Attributes:
        database_url: PostgreSQL async connection string.
        secret_key: JWT signing key (min 32 chars).
        algorithm: JWT algorithm (default HS256).
        access_token_expire_minutes: Access token lifetime.
        refresh_token_expire_days: Refresh token lifetime.
        face_tolerance: Face recognition distance threshold.
        upload_dir: Directory for uploaded files.
        max_upload_size_mb: Maximum upload size in MB.
        allowed_origins: CORS allowed origins (comma-separated).
        environment: Runtime environment (development/production).
        log_level: Logging level.
        debug: Enable debug mode.
    """

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://faceattend:password@localhost:5432/faceattend"
    secret_key: str = "CHANGE_THIS_TO_A_RANDOM_64_CHAR_STRING"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    face_tolerance: float = 0.6
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 10
    allowed_origins: str = "http://localhost:5173,http://localhost:3000"
    environment: str = "development"
    log_level: str = "INFO"

    @property
    def origins_list(self) -> List[str]:
        """Parse allowed origins string into a list.

        Returns:
            List of allowed origin URLs.
        """
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def debug(self) -> bool:
        """Check if running in development mode.

        Returns:
            True if environment is development.
        """
        return self.environment == "development"

    @property
    def max_upload_bytes(self) -> int:
        """Convert max upload size to bytes.

        Returns:
            Maximum upload size in bytes.
        """
        return self.max_upload_size_mb * 1024 * 1024


settings = Settings()
