from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "PartsDB"
    debug: bool = False

    secret_key: str = "dev-secret-change-me"
    access_token_expire_minutes: int = 10080

    database_url: str = (
        "postgresql+psycopg://partsdb:partsdb@localhost:5432/partsdb"
    )

    admin_username: str = "admin"
    admin_password: str = "admin"
    admin_email: str = "admin@example.com"

    attachments_dir: str = "data/attachments"
    backups_dir: str = "data/backups"

    lcsc_api_key: str = ""
    digikey_client_id: str = ""
    digikey_client_secret: str = ""
    digikey_api_token: str = ""

    ai_provider: str = "none"
    ai_api_key: str = ""
    ai_base_url: str = ""
    ai_model: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def ai_enabled(self) -> bool:
        return self.ai_base_url != "" or (self.ai_provider not in ("", "none"))

    @property
    def ai_resolved_url(self) -> str:
        """The chat-completions base URL, taken from AI_BASE_URL or AI_PROVIDER."""
        if self.ai_base_url:
            return self.ai_base_url.rstrip("/")
        if self.ai_provider not in ("", "none"):
            return self.ai_provider.rstrip("/")
        return ""

    @property
    def attachments_path(self) -> Path:
        return Path(self.attachments_dir)

    @property
    def backups_path(self) -> Path:
        return Path(self.backups_dir)


@lru_cache
def get_settings() -> Settings:
    return Settings()
