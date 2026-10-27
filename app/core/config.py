from functools import lru_cache
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = Field(..., env="DATABASE_URL")

    jwt_secret: str = Field(..., env="JWT_SECRET")
    encryption_key: str = Field(..., env="ENCRYPTION_KEY")

    atlassian_client_id: str = Field(..., env="ATLASSIAN_CLIENT_ID")
    atlassian_client_secret: str = Field(..., env="ATLASSIAN_CLIENT_SECRET")
    atlassian_redirect_uri: str = Field(..., env="ATLASSIAN_REDIRECT_URI")

    atlassian_auth_url: str = Field(
        default="https://auth.atlassian.com/authorize",
        env="ATLASSIAN_AUTH_URL",
    )
    atlassian_token_url: str = Field(
        default="https://auth.atlassian.com/oauth/token",
        env="ATLASSIAN_TOKEN_URL",
    )
    atlassian_api_base: str = Field(
        default="https://api.atlassian.com",
        env="ATLASSIAN_API_BASE",
    )

    gemini_model: str = Field(
        default="gemini-2.5-flash-lite",
        env="GEMINI_MODEL"
    )

    gemini_proxy_url: str = Field(
        default="https://geminiproxy.rajpootanmol779.workers.dev",
        env="GEMINI_PROXY_URL"
    )

    app_env: str = Field(
        default="development",
        env="APP_ENV"
    )

    frontend_url: str = Field(
        default="http://127.0.0.1:8000",
        env="FRONTEND_URL"
    )

    cors_origins: str = Field(
        default="http://127.0.0.1:8000,http://localhost:8000",
        env="CORS_ORIGINS"
    )

    rate_limit_requests: int = Field(
        default=120,
        env="RATE_LIMIT_REQUESTS"
    )

    rate_limit_window_seconds: int = Field(
        default=60,
        env="RATE_LIMIT_WINDOW_SECONDS"
    )

    access_token_expire_minutes: int = Field(
        default=60 * 24,
        env="ACCESS_TOKEN_EXPIRE_MINUTES"
    )

    atlassian_scopes: str = Field(
        default="read:jira-work write:jira-work read:jira-user offline_access",
        env="ATLASSIAN_SCOPES",
    )

    @property
    def oauth_scopes(self) -> str:
        return self.atlassian_scopes

    @property
    def sqlalchemy_database_url(self) -> str:
        url = self.database_url.strip()

        # Render/Neon compatibility
        if url.startswith("postgres://"):
            url = url.replace(
                "postgres://",
                "postgresql+asyncpg://",
                1
            )

        elif url.startswith("postgresql://"):
            url = url.replace(
                "postgresql://",
                "postgresql+asyncpg://",
                1
            )

        parsed = urlparse(url)

        query_params = dict(parse_qsl(parsed.query))

        # Remove params unsupported by asyncpg
        query_params.pop("sslmode", None)
        query_params.pop("channel_binding", None)

        cleaned_url = urlunparse(
            parsed._replace(query=urlencode(query_params))
        )

        return cleaned_url

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