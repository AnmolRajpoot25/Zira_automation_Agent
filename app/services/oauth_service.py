import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.crypto import decrypt_value, encrypt_value
from app.models.user import JiraConnection, User

logger = logging.getLogger(__name__)
settings = get_settings()


class JiraOAuthError(Exception):
    """Base exception for Jira OAuth and API operations."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class JiraResourceNotFoundError(JiraOAuthError):
    """Raised when no accessible Jira site or resource can be found."""

    def __init__(self, message: str = "No accessible Jira sites found."):
        super().__init__(message, status_code=404)


class JiraAuthenticationError(JiraOAuthError):
    """Raised when authentication fails (token expired, revoked, invalid)."""

    def __init__(self, message: str = "Jira authentication failed. Please reconnect Jira."):
        super().__init__(message, status_code=401)


class JiraPermissionError(JiraOAuthError):
    """Raised when required OAuth scopes or site permissions are missing."""

    def __init__(self, message: str = "Insufficient permissions for Jira operation."):
        super().__init__(message, status_code=403)


class JiraAPIError(JiraOAuthError):
    """Raised when Jira API calls fail with non-auth status codes or network issues."""

    def __init__(self, status_code: int = 502, detail: str = "Jira API communication error."):
        super().__init__(detail, status_code=status_code)
        self.detail = detail


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
    try:
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
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=15,
            )
            if response.status_code in (400, 401):
                logger.warning("Atlassian code exchange failed with status %d", response.status_code)
                raise JiraAuthenticationError("Authorization code is invalid or has expired.")
            response.raise_for_status()
            token_data = response.json()
            if not isinstance(token_data, dict) or "access_token" not in token_data:
                raise JiraOAuthError("Malformed token response from Atlassian.")
            return token_data
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        logger.error("Network error during Atlassian token exchange: %s", exc)
        raise JiraAPIError(status_code=504, detail="Timeout contacting Atlassian authorization server.") from exc
    except httpx.HTTPStatusError as exc:
        logger.error("HTTP error during Atlassian token exchange: %d", exc.response.status_code)
        raise JiraOAuthError("Failed to exchange authorization code for tokens.") from exc


async def fetch_cloud_id(access_token: str, preferred_cloud_id: str | None = None) -> str:
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.atlassian_api_base}/oauth/token/accessible-resources",
                headers=headers,
                timeout=15,
            )
            if response.status_code in (401, 403):
                logger.warning("Failed to fetch accessible resources: HTTP %d", response.status_code)
                raise JiraAuthenticationError("Jira access token expired or unauthorized.")
            response.raise_for_status()
            sites = response.json()
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        logger.error("Network error fetching accessible resources: %s", exc)
        raise JiraAPIError(status_code=504, detail="Timeout contacting Atlassian accessible-resources API.") from exc
    except httpx.HTTPStatusError as exc:
        logger.error("HTTP error fetching accessible resources: %d", exc.response.status_code)
        raise JiraAPIError(status_code=exc.response.status_code, detail="Error fetching Atlassian accessible resources.") from exc

    if not isinstance(sites, list):
        raise JiraOAuthError("Malformed response from Atlassian accessible resources endpoint.")

    if not sites:
        raise JiraResourceNotFoundError("No accessible Atlassian sites found for this account.")

    # Filter sites that have Jira capabilities/scopes
    jira_sites = [
        site for site in sites
        if isinstance(site, dict) and any("jira" in str(s).lower() for s in site.get("scopes", []))
    ]

    if not jira_sites:
        raise JiraPermissionError(
            "Accessible Atlassian sites found, but none have Jira scopes authorized. "
            "Please ensure you grant Jira permissions during authorization."
        )

    # If preferred_cloud_id was requested and is available among Jira sites, use it
    if preferred_cloud_id:
        for site in jira_sites:
            if site.get("id") == preferred_cloud_id:
                return site["id"].strip()

    # If multiple Jira sites are accessible, select the best candidate
    if len(jira_sites) > 1:
        site_names = [s.get("name", "unnamed") for s in jira_sites]
        logger.info("Multiple accessible Jira sites found: %s. Selecting primary site.", site_names)
        # Prioritize site with both read:jira-user and read:jira-work
        complete_scope_sites = [
            s for s in jira_sites
            if "read:jira-user" in s.get("scopes", []) and "read:jira-work" in s.get("scopes", [])
        ]
        if complete_scope_sites:
            return complete_scope_sites[0]["id"].strip()

    selected_id = jira_sites[0].get("id")
    if not selected_id:
        raise JiraOAuthError("Selected Jira site is missing an ID.")
    return selected_id.strip()


async def fetch_current_jira_user(access_token: str, cloud_id: str) -> dict:
    if not access_token or not cloud_id:
        raise JiraAuthenticationError("Missing access token or cloud ID.")

    clean_cloud_id = cloud_id.strip()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }
    url = f"{settings.atlassian_api_base}/ex/jira/{clean_cloud_id}/rest/api/3/myself"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=15)
            if response.status_code == 401:
                logger.warning("Jira API returned 401 for cloud ID %s", clean_cloud_id)
                raise JiraAuthenticationError("Jira access token expired or invalid.")
            elif response.status_code == 403:
                logger.warning("Jira API returned 403 for cloud ID %s", clean_cloud_id)
                raise JiraPermissionError("Insufficient permissions to view Jira user identity. Required scope: read:jira-user.")
            elif response.status_code == 404:
                logger.warning("Jira API returned 404 for cloud ID %s at %s", clean_cloud_id, url)
                raise JiraResourceNotFoundError(
                    f"Jira site or endpoint not found for cloud ID '{clean_cloud_id}'. "
                    "The site may be inactive, renamed, or access was revoked."
                )
            elif response.status_code == 429:
                logger.warning("Jira API rate limit exceeded")
                raise JiraAPIError(status_code=429, detail="Jira API rate limit exceeded. Please try again shortly.")
            elif response.status_code >= 500:
                logger.error("Jira API server error: %d", response.status_code)
                raise JiraAPIError(status_code=response.status_code, detail="Atlassian Jira service error.")
            
            response.raise_for_status()
            data = response.json()
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        logger.error("Network error communicating with Jira API: %s", exc)
        raise JiraAPIError(status_code=504, detail="Timeout communicating with Jira API.") from exc
    except httpx.HTTPStatusError as exc:
        logger.error("HTTP error communicating with Jira API: %d", exc.response.status_code)
        raise JiraAPIError(status_code=exc.response.status_code, detail="Jira API error.") from exc

    if not isinstance(data, dict) or "accountId" not in data:
        raise JiraAPIError(status_code=502, detail="Jira user profile response missing required accountId.")

    return data


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

    connection.cloud_id = cloud_id.strip()
    connection.encrypted_access_token = encrypt_value(token_data["access_token"])
    if token_data.get("refresh_token"):
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
    if not refresh_token:
        raise JiraAuthenticationError("Unable to decrypt refresh token. Please reconnect Jira.")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.atlassian_token_url,
                json={
                    "grant_type": "refresh_token",
                    "client_id": settings.atlassian_client_id,
                    "client_secret": settings.atlassian_client_secret,
                    "refresh_token": refresh_token,
                },
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=15,
            )
            if response.status_code in (400, 401):
                logger.warning("Atlassian token refresh rejected with status %d", response.status_code)
                raise JiraAuthenticationError("Jira refresh token is invalid or has expired. Please reconnect Jira.")
            response.raise_for_status()
            token_data = response.json()
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        logger.error("Network error during Jira token refresh: %s", exc)
        raise JiraAPIError(status_code=504, detail="Timeout contacting Atlassian token refresh endpoint.") from exc
    except httpx.HTTPStatusError as exc:
        logger.error("HTTP error during Jira token refresh: %d", exc.response.status_code)
        raise JiraAuthenticationError("Failed to refresh Jira access token. Please reconnect Jira.") from exc

    if not isinstance(token_data, dict) or "access_token" not in token_data:
        raise JiraOAuthError("Malformed token response received from Atlassian during refresh.")

    expires_in = token_data.get("expires_in", 3600)
    connection.encrypted_access_token = encrypt_value(token_data["access_token"])
    # Handle refresh token rotation if a new refresh token is provided
    if token_data.get("refresh_token"):
        connection.encrypted_refresh_token = encrypt_value(token_data["refresh_token"])
    connection.expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    try:
        await db.commit()
        await db.refresh(connection)
    except Exception as exc:
        await db.rollback()
        logger.error("Failed to persist refreshed Jira tokens: %s", exc)
        raise JiraOAuthError("Database error persisting refreshed tokens.") from exc

    return connection


async def get_valid_access_token(
    db: AsyncSession,
    connection: JiraConnection,
) -> str:
    expires_at = connection.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    # 60-second buffer to prevent token expiration mid-request
    if datetime.now(timezone.utc) >= expires_at - timedelta(seconds=60):
        connection = await refresh_access_token(db, connection)

    token = decrypt_value(connection.encrypted_access_token)
    if token is None:
        # If decryption failed, try refreshing once if refresh token is present
        if connection.encrypted_refresh_token:
            connection = await refresh_access_token(db, connection)
            token = decrypt_value(connection.encrypted_access_token)

    if token is None:
        raise JiraAuthenticationError("Missing or undecryptable Jira access token. Please reconnect Jira.")

    return token
