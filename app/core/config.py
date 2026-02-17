import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv() -> None:
    dotenv_path = PROJECT_ROOT / ".env"
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        os.environ.setdefault(key, value)


class Settings(BaseModel):
    app_name: str = Field(default="CapLedger")
    environment: str = Field(default="development")
    debug: bool = Field(default=False)
    database_url: str = Field(default="sqlite:///./esop.db")
    esop_pool_size: int = Field(default=1_000_000)
    cors_origins: str = Field(default="*")
    session_secret_key: str = Field(default="change-this-secret")
    session_cookie_secure: bool = Field(default=False)
    google_client_id: str | None = Field(default=None)
    google_client_secret: str | None = Field(default=None)
    google_org_domain: str | None = Field(default=None)
    admin_emails: str = Field(default="")
    auth_enabled: bool = Field(default=True)

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def admin_email_list(self) -> list[str]:
        return [email.strip().lower() for email in self.admin_emails.split(",") if email.strip()]

    @classmethod
    def from_environment(cls) -> "Settings":
        _load_dotenv()
        return cls(
            app_name=os.getenv("APP_NAME", "CapLedger"),
            environment=os.getenv("ENVIRONMENT", "development"),
            debug=os.getenv("DEBUG", "false").lower() in {"1", "true", "yes", "on"},
            database_url=os.getenv("DATABASE_URL", "sqlite:///./esop.db"),
            esop_pool_size=int(os.getenv("ESOP_POOL_SIZE", "1000000")),
            cors_origins=os.getenv("CORS_ORIGINS", "*"),
            session_secret_key=os.getenv("SESSION_SECRET_KEY", "change-this-secret"),
            session_cookie_secure=os.getenv("SESSION_COOKIE_SECURE", "false").lower() in {"1", "true", "yes", "on"},
            google_client_id=os.getenv("GOOGLE_CLIENT_ID"),
            google_client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
            google_org_domain=os.getenv("GOOGLE_ORG_DOMAIN"),
            admin_emails=os.getenv("ADMIN_EMAILS", ""),
            auth_enabled=os.getenv("AUTH_ENABLED", "true").lower() in {"1", "true", "yes", "on"},
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_environment()
