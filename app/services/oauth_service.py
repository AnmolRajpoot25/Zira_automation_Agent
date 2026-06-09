from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.crypto import decrypt_value, encrypt_value
from app.models.user import JiraConnection, User

settings = get_settings()


def build_authorization_url(state: str) -> str:
    params = {
        "audience": "api.atlassian.com",
        "client_id": settings.atlassian_client_id,
        "scope": settings.oauth_scopes,
        "redirect_uri": settings.atlassian_redirect_uri,
        "state": state,
        "response_type": "code",
        "prompt": "consent",
    }
    return f"{settings.atlassian_auth_url}?{urlencode(params)}"


async def exchange_code_for_tokens(code: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            settings.atlassian_token_url,
            json={
                "grant_type": "authorization_code",
                "client_id": settings.atlassian_client_id,
                "client_secret": settings.atlassian_client_secret,
                "code": code,
                "redirect_uri": settings.atlassian_redirect_uri,
            },
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        response.raise_for_status()
        return response.json()


async def fetch_cloud_id(access_token: str) -> str:
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.atlassian_api_base}/oauth/token/accessible-resources",
            headers=headers,
            timeout=15,
        )
        response.raise_for_status()
        sites = response.json()
    if not sites:
        raise ValueError("No accessible Jira sites found.")
    return sites[0]["id"]


async def fetch_current_jira_user(access_token: str, cloud_id: str) -> dict:
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.atlassian_api_base}/ex/jira/{cloud_id}/rest/api/3/myself",
            headers=headers,
            timeout=15,
        )
        response.raise_for_status()
        return response.json()


async def upsert_jira_connection(
    db: AsyncSession,
    user: User,
    cloud_id: str,
    token_data: dict,
) -> JiraConnection:
    expires_in = token_data.get("expires_in", 3600)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    result = await db.execute(
        select(JiraConnection).where(JiraConnection.user_id == user.id)
    )
    connection = result.scalar_one_or_none()
    if connection is None:
        connection = JiraConnection(user_id=user.id)
        db.add(connection)

    connection.cloud_id = cloud_id
    connection.encrypted_access_token = encrypt_value(token_data["access_token"])
    connection.encrypted_refresh_token = encrypt_value(token_data["refresh_token"])
    connection.expires_at = expires_at

    await db.commit()
    await db.refresh(connection)
    return connection


async def refresh_access_token(
    db: AsyncSession,
    connection: JiraConnection,
) -> JiraConnection:
    refresh_token = decrypt_value(connection.encrypted_refresh_token)
    async with httpx.AsyncClient() as client:
        response = await client.post(
            settings.atlassian_token_url,
            json={
                "grant_type": "refresh_token",
                "client_id": settings.atlassian_client_id,
                "client_secret": settings.atlassian_client_secret,
                "refresh_token": refresh_token,
            },
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        response.raise_for_status()
        token_data = response.json()

    expires_in = token_data.get("expires_in", 3600)
    connection.encrypted_access_token = encrypt_value(token_data["access_token"])
    if token_data.get("refresh_token"):
        connection.encrypted_refresh_token = encrypt_value(token_data["refresh_token"])
    connection.expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    await db.commit()
    await db.refresh(connection)
    return connection


async def get_valid_access_token(
    db: AsyncSession,
    connection: JiraConnection,
) -> str:
    expires_at = connection.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) >= expires_at:
        connection = await refresh_access_token(db, connection)
    token = decrypt_value(connection.encrypted_access_token)
    if token is None:
        raise ValueError("Missing Jira access token.")
    return token
