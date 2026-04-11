import secrets
import httpx
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import get_settings
from app.core.crypto import encrypt_token, decrypt_token
from app.models.user import User

settings = get_settings()


def build_authorization_url(state: str | None = None) -> tuple[str, str]:
    if state is None:
        state = secrets.token_urlsafe(32)
    params = {
        "audience": "api.atlassian.com",
        "client_id": settings.atlassian_client_id,
        "scope": settings.oauth_scopes,
        "redirect_uri": settings.atlassian_redirect_uri,
        "state": state,
        "response_type": "code",
        "prompt": "consent",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{settings.atlassian_auth_url}?{query}", state


async def exchange_code_for_tokens(code: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
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
        resp.raise_for_status()
        return resp.json()


async def fetch_user_identity(access_token: str) -> dict:
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient() as client:
        # Get accessible Jira sites
        sites_resp = await client.get(
            f"{settings.atlassian_api_base}/oauth/token/accessible-resources",
            headers=headers,
            timeout=15,
        )
        sites_resp.raise_for_status()
        sites = sites_resp.json()

        if not sites:
            raise ValueError("No accessible Jira sites found.")

        site = sites[0]
        cloud_id = site["id"]
        jira_base_url = site["url"]

        # Use Jira's own /myself endpoint instead of /me
        # (covered by read:jira-user, no need for read:me scope)
        me_resp = await client.get(
            f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/myself",
            headers=headers,
            timeout=15,
        )
        me_resp.raise_for_status()
        me = me_resp.json()

    return {
        "account_id": me["accountId"],
        "email": me.get("emailAddress", ""),
        "display_name": me.get("displayName", ""),
        "cloud_id": cloud_id,
        "jira_base_url": jira_base_url,
    }

async def upsert_user(db: AsyncSession, identity: dict, token_data: dict) -> User:
    expires_in = token_data.get("expires_in", 3600)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    result = await db.execute(
        select(User).where(User.account_id == identity["account_id"])
    )
    user = result.scalar_one_or_none()

    if user is None:
        user = User(account_id=identity["account_id"])
        db.add(user)

    user.email = identity["email"]
    user.display_name = identity["display_name"]
    user.cloud_id = identity["cloud_id"]
    user.jira_base_url = identity["jira_base_url"]
    user.access_token_enc = encrypt_token(token_data["access_token"])
    user.refresh_token_enc = encrypt_token(token_data.get("refresh_token", "no_refresh_token"))
    user.token_expires_at = expires_at

    await db.commit()
    await db.refresh(user)
    return user


async def refresh_access_token(db: AsyncSession, user: User) -> User:
    refresh_token = decrypt_token(user.refresh_token_enc)
    async with httpx.AsyncClient() as client:
        resp = await client.post(
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
        resp.raise_for_status()
        token_data = resp.json()

    expires_in = token_data.get("expires_in", 3600)
    user.access_token_enc = encrypt_token(token_data["access_token"])
    if "refresh_token" in token_data:
        user.refresh_token_enc = encrypt_token(token_data.get("refresh_token", "no_refresh_token"))
    user.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    await db.commit()
    await db.refresh(user)
    return user


async def get_valid_access_token(db: AsyncSession, user: User) -> str:
    if datetime.now(timezone.utc) >= user.token_expires_at.replace(tzinfo=timezone.utc) if user.token_expires_at.tzinfo is None else user.token_expires_at:
        user = await refresh_access_token(db, user)
    return decrypt_token(user.access_token_enc)
