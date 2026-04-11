from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    atlassian_client_id: str = Field(..., env="ATLASSIAN_CLIENT_ID")
    atlassian_client_secret: str = Field(..., env="ATLASSIAN_CLIENT_SECRET")
    atlassian_redirect_uri: str = Field(..., env="ATLASSIAN_REDIRECT_URI")

    atlassian_auth_url: str = "https://auth.atlassian.com/authorize"
    atlassian_token_url: str = "https://auth.atlassian.com/oauth/token"
    atlassian_api_base: str = "https://api.atlassian.com"

    gemini_api_key: str = Field(..., env="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.5-flash", env="GEMINI_MODEL")

    secret_key: str = Field(..., env="SECRET_KEY")
    encryption_key: str = Field(..., env="ENCRYPTION_KEY")

    database_url: str = Field(
        default="sqlite+aiosqlite:///./jira_agent.db", env="DATABASE_URL"
    )

    app_env: str = Field(default="development", env="APP_ENV")
    frontend_url: str = Field(default="http://127.0.0.1:8000", env="FRONTEND_URL")

    oauth_scopes: str = (
        "read:jira-work write:jira-work read:jira-user"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()