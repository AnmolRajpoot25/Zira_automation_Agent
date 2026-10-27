import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
import httpx

from app.services import oauth_service
from app.services.oauth_service import (
    JiraOAuthError,
    JiraResourceNotFoundError,
    JiraAuthenticationError,
    JiraPermissionError,
    JiraAPIError,
    fetch_cloud_id,
    fetch_current_jira_user,
    refresh_access_token,
    get_valid_access_token,
)
from app.models.user import JiraConnection, User


class TestJiraOAuthService(unittest.TestCase):

    # ── Test 1: Successful accessible-resource discovery ──────────────────────
    def test_01_successful_accessible_resource_discovery(self):
        async def run_test():
            mock_sites = [
                {
                    "id": "jira-cloud-abc-123",
                    "name": "My Company Jira",
                    "url": "https://mycompany.atlassian.net",
                    "scopes": ["read:jira-work", "write:jira-work", "read:jira-user"],
                }
            ]
            mock_resp = MagicMock(spec=httpx.Response)
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_sites

            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_resp
                cloud_id = await fetch_cloud_id("fake-access-token")
                self.assertEqual(cloud_id, "jira-cloud-abc-123")
                mock_get.assert_called_once()
                # Verify required Accept header was included
                call_headers = mock_get.call_args[1]["headers"]
                self.assertEqual(call_headers.get("Accept"), "application/json")
                self.assertEqual(call_headers.get("Authorization"), "Bearer fake-access-token")

        asyncio.run(run_test())

    # ── Test 2: Multiple accessible Jira sites ────────────────────────────────
    def test_02_multiple_accessible_sites_filtering(self):
        async def run_test():
            # First resource is a Confluence site with NO Jira scopes.
            # Second resource is the actual Jira site.
            mock_sites = [
                {
                    "id": "confluence-non-jira-id",
                    "name": "Company Wiki",
                    "url": "https://wiki.atlassian.net",
                    "scopes": ["read:confluence-content", "write:confluence-space"],
                },
                {
                    "id": "real-jira-cloud-id",
                    "name": "Company Jira Tracker",
                    "url": "https://tracker.atlassian.net",
                    "scopes": ["read:jira-work", "write:jira-work", "read:jira-user"],
                },
            ]
            mock_resp = MagicMock(spec=httpx.Response)
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_sites

            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_resp
                # Must NOT choose the first resource because it lacks Jira scopes
                cloud_id = await fetch_cloud_id("fake-token")
                self.assertEqual(cloud_id, "real-jira-cloud-id")

        asyncio.run(run_test())

    def test_02b_preferred_cloud_id_selection(self):
        async def run_test():
            mock_sites = [
                {
                    "id": "jira-site-1",
                    "name": "Jira Site 1",
                    "scopes": ["read:jira-work", "read:jira-user"],
                },
                {
                    "id": "jira-site-2",
                    "name": "Jira Site 2",
                    "scopes": ["read:jira-work", "read:jira-user"],
                },
            ]
            mock_resp = MagicMock(spec=httpx.Response)
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_sites

            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_resp
                # Specifying preferred_cloud_id should return that exact site
                cloud_id = await fetch_cloud_id("fake-token", preferred_cloud_id="jira-site-2")
                self.assertEqual(cloud_id, "jira-site-2")

        asyncio.run(run_test())

    # ── Test 3: No accessible resources ───────────────────────────────────────
    def test_03_no_accessible_resources_empty_list(self):
        async def run_test():
            mock_resp = MagicMock(spec=httpx.Response)
            mock_resp.status_code = 200
            mock_resp.json.return_value = []

            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_resp
                with self.assertRaises(JiraResourceNotFoundError) as ctx:
                    await fetch_cloud_id("fake-token")
                self.assertIn("No accessible Atlassian sites found", str(ctx.exception))

        asyncio.run(run_test())

    def test_03b_no_jira_scopes_in_accessible_resources(self):
        async def run_test():
            mock_sites = [
                {
                    "id": "only-confluence",
                    "name": "Wiki Only",
                    "scopes": ["read:confluence-content"],
                }
            ]
            mock_resp = MagicMock(spec=httpx.Response)
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_sites

            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_resp
                with self.assertRaises(JiraPermissionError) as ctx:
                    await fetch_cloud_id("fake-token")
                self.assertIn("none have Jira scopes", str(ctx.exception))

        asyncio.run(run_test())

    # ── Test 4: Successful current-user retrieval ──────────────────────────────
    def test_04_successful_current_user_retrieval(self):
        async def run_test():
            mock_user_data = {
                "accountId": "712020:5c7d8e9f-1234-5678-9abc-def012345678",
                "displayName": "Jane Doe",
                "emailAddress": "jane@example.com",
                "active": True,
            }
            mock_resp = MagicMock(spec=httpx.Response)
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_user_data

            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_resp
                user_info = await fetch_current_jira_user("test-token", "test-cloud-id")
                self.assertEqual(user_info["accountId"], mock_user_data["accountId"])
                self.assertEqual(user_info["displayName"], "Jane Doe")

                # Verify URL and content-negotiation headers
                call_args = mock_get.call_args
                url = call_args[0][0]
                self.assertIn("/ex/jira/test-cloud-id/rest/api/3/myself", url)
                self.assertEqual(call_args[1]["headers"]["Accept"], "application/json")
                self.assertEqual(call_args[1]["headers"]["Authorization"], "Bearer test-token")

        asyncio.run(run_test())

    # ── Test 5: HTTP 404 handling ─────────────────────────────────────────────
    def test_05_http_404_handling(self):
        async def run_test():
            mock_resp = MagicMock(spec=httpx.Response)
            mock_resp.status_code = 404
            mock_resp.text = "Site not found"

            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_resp
                with self.assertRaises(JiraResourceNotFoundError) as ctx:
                    await fetch_current_jira_user("secret-token-123", "non-existent-cloud-id")
                
                # Check error message is informative and does NOT leak secret token
                error_msg = str(ctx.exception)
                self.assertIn("non-existent-cloud-id", error_msg)
                self.assertNotIn("secret-token-123", error_msg)

        asyncio.run(run_test())

    # ── Test 6: HTTP 401 and 403 handling ──────────────────────────────────────
    def test_06_http_401_and_403_handling(self):
        async def run_test():
            # Test 401 Unauthorized
            mock_401 = MagicMock(spec=httpx.Response)
            mock_401.status_code = 401

            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_401
                with self.assertRaises(JiraAuthenticationError):
                    await fetch_current_jira_user("expired-token", "cloud-123")

            # Test 403 Forbidden
            mock_403 = MagicMock(spec=httpx.Response)
            mock_403.status_code = 403

            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_403
                with self.assertRaises(JiraPermissionError) as ctx:
                    await fetch_current_jira_user("token", "cloud-123")
                self.assertIn("read:jira-user", str(ctx.exception))

        asyncio.run(run_test())

    # ── Test 7: Token refresh & rotation ──────────────────────────────────────
    def test_07_token_refresh_and_rotation(self):
        async def run_test():
            # Set up mock JiraConnection with encrypted tokens
            from app.core.crypto import encrypt_value, decrypt_value

            old_refresh = "old-refresh-token-xyz"
            old_access = "old-access-token-abc"
            conn = JiraConnection(
                id=1,
                user_id=10,
                cloud_id="cloud-123",
                encrypted_access_token=encrypt_value(old_access),
                encrypted_refresh_token=encrypt_value(old_refresh),
                expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
            )

            mock_refresh_response = {
                "access_token": "new-access-token-123",
                "refresh_token": "new-rotated-refresh-token-456",
                "expires_in": 3600,
            }
            mock_resp = MagicMock(spec=httpx.Response)
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_refresh_response

            mock_db = AsyncMock()

            with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
                mock_post.return_value = mock_resp
                updated_conn = await refresh_access_token(mock_db, conn)

                # Verify tokens were updated and rotated
                new_access_decrypted = decrypt_value(updated_conn.encrypted_access_token)
                new_refresh_decrypted = decrypt_value(updated_conn.encrypted_refresh_token)
                self.assertEqual(new_access_decrypted, "new-access-token-123")
                self.assertEqual(new_refresh_decrypted, "new-rotated-refresh-token-456")
                self.assertGreater(updated_conn.expires_at, datetime.now(timezone.utc))
                mock_db.commit.assert_called_once()

        asyncio.run(run_test())

    # ── Test 8: Network errors & timeouts ─────────────────────────────────────
    def test_08_network_errors_handled_cleanly(self):
        async def run_test():
            # Test timeout
            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_get.side_effect = httpx.TimeoutException("Connection timed out")
                with self.assertRaises(JiraAPIError) as ctx:
                    await fetch_current_jira_user("token", "cloud-123")
                self.assertEqual(ctx.exception.status_code, 504)
                self.assertIn("Timeout", ctx.exception.detail)

            # Test connection error
            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_get.side_effect = httpx.ConnectError("Connection refused")
                with self.assertRaises(JiraAPIError) as ctx:
                    await fetch_current_jira_user("token", "cloud-123")
                self.assertEqual(ctx.exception.status_code, 504)

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
