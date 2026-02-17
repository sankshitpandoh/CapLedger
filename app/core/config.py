import os
from functools import lru_cache

from pydantic import BaseModel, Field


class Settings(BaseModel):
    app_name: str = Field(default="ESOP Management Tool")
    environment: str = Field(default="development")
    debug: bool = Field(default=False)
    database_url: str = Field(default="sqlite:///./esop.db")
    esop_pool_size: int = Field(default=1_000_000)
    cors_origins: str = Field(default="*")

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            app_name=os.getenv("APP_NAME", "ESOP Management Tool"),
            environment=os.getenv("ENVIRONMENT", "development"),
            debug=os.getenv("DEBUG", "false").lower() in {"1", "true", "yes", "on"},
            database_url=os.getenv("DATABASE_URL", "sqlite:///./esop.db"),
            esop_pool_size=int(os.getenv("ESOP_POOL_SIZE", "1000000")),
            cors_origins=os.getenv("CORS_ORIGINS", "*"),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_environment()
