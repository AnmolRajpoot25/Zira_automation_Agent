from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = Field(..., env="DATABASE_URL")

    jwt_secret: str = Field(..., env="JWT_SECRET")
    encryption_key: str = Field(..., env="ENCRYPTION_KEY")

    atlassian_client_id: str = Field(..., env="ATLASSIAN_CLIENT_ID")
    atlassian_client_secret: str = Field(..., env="ATLASSIAN_CLIENT_SECRET")
    atlassian_redirect_uri: str = Field(..., env="ATLASSIAN_REDIRECT_URI")

    atlassian_auth_url: str = "https://auth.atlassian.com/authorize"
    atlassian_token_url: str = "https://auth.atlassian.com/oauth/token"
    atlassian_api_base: str = "https://api.atlassian.com"

    gemini_model: str = Field(
        default="gemini-2.5-flash",
        env="GEMINI_MODEL",
    )

    app_env: str = Field(
        default="development",
        env="APP_ENV",
    )

    frontend_url: str = Field(
        default="http://127.0.0.1:8000",
        env="FRONTEND_URL",
    )

    cors_origins: str = Field(
        default="http://127.0.0.1:8000,http://localhost:8000",
        env="CORS_ORIGINS",
    )

    rate_limit_requests: int = Field(
        default=120,
        env="RATE_LIMIT_REQUESTS",
    )

    rate_limit_window_seconds: int = Field(
        default=60,
        env="RATE_LIMIT_WINDOW_SECONDS",
    )

    access_token_expire_minutes: int = Field(
        default=60 * 24,
        env="ACCESS_TOKEN_EXPIRE_MINUTES",
    )

    oauth_scopes: str = (
        "read:jira-work write:jira-work "
        "read:jira-user offline_access"
    )

    @property
    def sqlalchemy_database_url(self) -> str:
        url = self.database_url

        if url.startswith("postgres://"):
            url = url.replace(
                "postgres://",
                "postgresql+asyncpg://",
                1,
            )

        elif url.startswith("postgresql://"):
            url = url.replace(
                "postgresql://",
                "postgresql+asyncpg://",
                1,
            )

        # Remove sslmode for asyncpg compatibility
        url = url.replace("?sslmode=require", "")

        return url

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [
            origin.strip().rstrip("/")
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

        frontend = self.frontend_url.rstrip("/")

        if frontend not in origins:
            origins.append(frontend)

        return origins

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()