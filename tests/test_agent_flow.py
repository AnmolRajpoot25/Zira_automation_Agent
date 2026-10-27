import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException

from app.models.user import JiraConnection, User
from app.services.agent_service import run_agent
from app.core.crypto import encrypt_value


class TestAgentFlow(unittest.TestCase):

    def test_09_agent_flow_success(self):
        async def run_test():
            # Set up mock user and connection
            user = User(
                id=1,
                name="Test User",
                email="test@example.com",
                encrypted_gemini_key=encrypt_value("fake-gemini-key"),
            )
            conn = JiraConnection(
                id=1,
                user_id=1,
                cloud_id="valid-cloud-id",
                encrypted_access_token=encrypt_value("valid-access-token"),
                encrypted_refresh_token=encrypt_value("valid-refresh-token"),
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )

            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = conn
            mock_db.execute.return_value = mock_result

            mock_identity = {
                "accountId": "jira-acc-123",
                "displayName": "Test User Jira",
                "emailAddress": "test@example.com",
            }

            with patch("app.services.agent_service.get_valid_access_token", new_callable=AsyncMock) as mock_get_token, \
                 patch("app.services.agent_service.fetch_current_jira_user", new_callable=AsyncMock) as mock_fetch_user, \
                 patch("google.generativeai.GenerativeModel") as mock_model_cls:

                mock_get_token.return_value = "valid-access-token"
                mock_fetch_user.return_value = mock_identity

                mock_chat = MagicMock()
                mock_model = MagicMock()
                mock_model.start_chat.return_value = mock_chat
                mock_model_cls.return_value = mock_model

                # Mock model response (no tool calls, direct answer)
                mock_part = MagicMock()
                mock_part.text = "Hello! How can I help you with Jira today?"
                del mock_part.function_call
                mock_candidate = MagicMock()
                mock_candidate.content.parts = [mock_part]
                mock_response = MagicMock()
                mock_response.candidates = [mock_candidate]
                mock_chat.send_message.return_value = mock_response

                result = await run_agent(mock_db, user, "Hello")

                mock_fetch_user.assert_called_once_with("valid-access-token", "valid-cloud-id")
                self.assertEqual(result["response"], "Hello! How can I help you with Jira today?")
                self.assertEqual(result["iterations"], 1)

        asyncio.run(run_test())

    def test_09b_agent_flow_recovers_from_stale_cloud_id(self):
        async def run_test():
            """Verifies that if stored cloud_id returns 404, the agent re-discovers the cloud ID."""
            from app.services.oauth_service import JiraResourceNotFoundError

            user = User(
                id=1,
                name="Test User",
                email="test@example.com",
                encrypted_gemini_key=encrypt_value("fake-gemini-key"),
            )
            conn = JiraConnection(
                id=1,
                user_id=1,
                cloud_id="stale-old-cloud-id",
                encrypted_access_token=encrypt_value("valid-access-token"),
                encrypted_refresh_token=encrypt_value("valid-refresh-token"),
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )

            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = conn
            mock_db.execute.return_value = mock_result

            mock_identity = {
                "accountId": "jira-acc-123",
                "displayName": "Test User Jira",
            }

            with patch("app.services.agent_service.get_valid_access_token", new_callable=AsyncMock) as mock_get_token, \
                 patch("app.services.agent_service.fetch_current_jira_user", new_callable=AsyncMock) as mock_fetch_user, \
                 patch("app.services.agent_service.fetch_cloud_id", new_callable=AsyncMock) as mock_fetch_cloud_id, \
                 patch("google.generativeai.GenerativeModel") as mock_model_cls:

                mock_get_token.return_value = "valid-access-token"

                # First call with stale cloud_id raises 404 (JiraResourceNotFoundError)
                # Second call with newly discovered cloud_id succeeds
                mock_fetch_user.side_effect = [
                    JiraResourceNotFoundError("Jira site not found for stale-old-cloud-id"),
                    mock_identity,
                ]
                mock_fetch_cloud_id.return_value = "newly-discovered-cloud-id"

                mock_chat = MagicMock()
                mock_model = MagicMock()
                mock_model.start_chat.return_value = mock_chat
                mock_model_cls.return_value = mock_model

                mock_part = MagicMock()
                mock_part.text = "I reconnected to your active Jira site and I'm ready."
                del mock_part.function_call
                mock_candidate = MagicMock()
                mock_candidate.content.parts = [mock_part]
                mock_response = MagicMock()
                mock_response.candidates = [mock_candidate]
                mock_chat.send_message.return_value = mock_response

                result = await run_agent(mock_db, user, "Show issues")

                # Verify that cloud_id on connection was updated to newly-discovered-cloud-id
                self.assertEqual(conn.cloud_id, "newly-discovered-cloud-id")
                # Verify db commit was called to save the new cloud ID
                mock_db.commit.assert_called()
                # Verify second call used new cloud ID
                mock_fetch_user.assert_called_with("valid-access-token", "newly-discovered-cloud-id")
                self.assertIn("ready", result["response"])

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
