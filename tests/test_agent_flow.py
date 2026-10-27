import asyncio
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from google.genai import types

from app.models.user import JiraConnection, User
from app.services.agent_service import run_agent, _build_gemini_tools
from app.core.crypto import encrypt_value


class TestAgentFlow(unittest.TestCase):

    def setUp(self):
        self.user = User(
            id=1,
            name="Anmol Rajput",
            email="rajpootanmol779@gmail.com",
            encrypted_gemini_key=encrypt_value("fake-gemini-key"),
        )
        self.conn = JiraConnection(
            id=1,
            user_id=1,
            cloud_id="cloud-123",
            encrypted_access_token=encrypt_value("valid-access-token"),
            encrypted_refresh_token=encrypt_value("valid-refresh-token"),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        self.mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = self.conn
        self.mock_db.execute.return_value = mock_result
        self.mock_identity = {
            "accountId": "jira-acc-123",
            "displayName": "Anmol Rajput",
        }

    # ── Test A: Single function call with namespaced default_api:get_projects ──
    def test_A_single_function_call_namespaced(self):
        async def run_test():
            fc = types.FunctionCall(name="default_api:get_projects", args={})
            p1 = types.Part(function_call=fc, thought_signature=b"test_thought_signature_xyz")
            resp1 = types.GenerateContentResponse(
                candidates=[types.Candidate(content=types.Content(role="model", parts=[p1]))]
            )

            p2 = types.Part(text="You have one project named ANMOL.")
            resp2 = types.GenerateContentResponse(
                candidates=[types.Candidate(content=types.Content(role="model", parts=[p2]))]
            )

            with patch("app.services.agent_service.get_valid_access_token", new_callable=AsyncMock) as mock_token, \
                 patch("app.services.agent_service.fetch_current_jira_user", new_callable=AsyncMock) as mock_user, \
                 patch("app.services.agent_service._execute_tool", new_callable=AsyncMock) as mock_tool, \
                 patch("google.genai.Client") as mock_client_cls:

                mock_token.return_value = "valid-access-token"
                mock_user.return_value = self.mock_identity
                mock_tool.return_value = json.dumps({"projects": [{"key": "ANMOL", "name": "ANMOL"}]})

                mock_client = MagicMock()
                mock_client.models.generate_content.side_effect = [resp1, resp2]
                mock_client_cls.return_value = mock_client

                res = await run_agent(self.mock_db, self.user, "What projects do I have?")

                self.assertEqual(res["response"], "You have one project named ANMOL.")
                self.assertEqual(len(res["tool_calls"]), 1)
                self.assertEqual(res["tool_calls"][0]["tool"], "get_projects")

                # Verify outgoing contents to model preserved the thought_signature on the model turn
                second_call_contents = mock_client.models.generate_content.call_args_list[1][1]["contents"]
                self.assertEqual(len(second_call_contents), 3)
                # Model turn (index 1) must retain thought_signature
                self.assertEqual(second_call_contents[1].parts[0].thought_signature, b"test_thought_signature_xyz")
                # Tool turn (index 2) must respond to the namespaced function name
                self.assertEqual(second_call_contents[2].parts[0].function_response.name, "default_api:get_projects")

        asyncio.run(run_test())

    # ── Test B: Multiple function calls in a single turn ───────────────────────
    def test_B_multiple_function_calls_in_one_response(self):
        async def run_test():
            fc1 = types.FunctionCall(name="get_current_user", args={})
            fc2 = types.FunctionCall(name="get_projects", args={})
            p1 = types.Part(function_call=fc1, thought_signature=b"multi_sig_1")
            p2 = types.Part(function_call=fc2, thought_signature=b"multi_sig_2")

            resp1 = types.GenerateContentResponse(
                candidates=[types.Candidate(content=types.Content(role="model", parts=[p1, p2]))]
            )

            p3 = types.Part(text="You are Anmol and your project is ANMOL.")
            resp2 = types.GenerateContentResponse(
                candidates=[types.Candidate(content=types.Content(role="model", parts=[p3]))]
            )

            with patch("app.services.agent_service.get_valid_access_token", new_callable=AsyncMock) as mock_token, \
                 patch("app.services.agent_service.fetch_current_jira_user", new_callable=AsyncMock) as mock_user, \
                 patch("app.services.agent_service._execute_tool", new_callable=AsyncMock) as mock_tool, \
                 patch("google.genai.Client") as mock_client_cls:

                mock_token.return_value = "valid-access-token"
                mock_user.return_value = self.mock_identity
                mock_tool.side_effect = [
                    json.dumps({"accountId": "jira-acc-123"}),
                    json.dumps({"projects": [{"key": "ANMOL"}]}),
                ]

                mock_client = MagicMock()
                mock_client.models.generate_content.side_effect = [resp1, resp2]
                mock_client_cls.return_value = mock_client

                res = await run_agent(self.mock_db, self.user, "Who am I and what projects do I have?")

                self.assertEqual(len(res["tool_calls"]), 2)
                second_call_contents = mock_client.models.generate_content.call_args_list[1][1]["contents"]
                # Verify that both function responses were sent in the user turn
                user_tool_parts = second_call_contents[2].parts
                self.assertEqual(len(user_tool_parts), 2)
                self.assertEqual(user_tool_parts[0].function_response.name, "get_current_user")
                self.assertEqual(user_tool_parts[1].function_response.name, "get_projects")

        asyncio.run(run_test())

    # ── Test C: Thought signature serialization test ──────────────────────────
    def test_C_metadata_thought_signature_serialization(self):
        fc = types.FunctionCall(name="create_issue", args={"project_key": "ANMOL", "summary": "Fix login"})
        part = types.Part(function_call=fc, thought_signature=b"binary_signature_bytes_abc")
        content = types.Content(role="model", parts=[part])

        # Test Pydantic model serialization performed by google-genai
        dumped = content.model_dump(by_alias=True, exclude_none=True)
        self.assertIn("thoughtSignature", dumped["parts"][0])
        self.assertEqual(dumped["parts"][0]["thoughtSignature"], b"binary_signature_bytes_abc")

    # ── Test D: Tool execution failure handled gracefully ─────────────────────
    def test_D_tool_failure_handled_gracefully(self):
        async def run_test():
            fc = types.FunctionCall(name="create_issue", args={"project_key": "INVALID", "summary": "Test"})
            resp1 = types.GenerateContentResponse(
                candidates=[types.Candidate(content=types.Content(role="model", parts=[types.Part(function_call=fc)]))]
            )
            resp2 = types.GenerateContentResponse(
                candidates=[types.Candidate(content=types.Content(role="model", parts=[types.Part(text="Project INVALID does not exist.")]))]
            )

            with patch("app.services.agent_service.get_valid_access_token", new_callable=AsyncMock) as mock_token, \
                 patch("app.services.agent_service.fetch_current_jira_user", new_callable=AsyncMock) as mock_user, \
                 patch("app.services.agent_service._execute_tool", new_callable=AsyncMock) as mock_tool, \
                 patch("google.genai.Client") as mock_client_cls:

                mock_token.return_value = "valid-access-token"
                mock_user.return_value = self.mock_identity
                mock_tool.return_value = json.dumps({"error": "Project 'INVALID' does not exist."})

                mock_client = MagicMock()
                mock_client.models.generate_content.side_effect = [resp1, resp2]
                mock_client_cls.return_value = mock_client

                res = await run_agent(self.mock_db, self.user, "Create issue in INVALID")

                self.assertEqual(res["tool_calls"][0]["result"], "Project 'INVALID' does not exist.")
                self.assertIn("Project INVALID does not exist", res["response"])

        asyncio.run(run_test())

    # ── Test E: Malformed model response handled safely ───────────────────────
    def test_E_malformed_model_response(self):
        async def run_test():
            # Response with empty candidates
            resp_empty = types.GenerateContentResponse(candidates=[])

            with patch("app.services.agent_service.get_valid_access_token", new_callable=AsyncMock) as mock_token, \
                 patch("app.services.agent_service.fetch_current_jira_user", new_callable=AsyncMock) as mock_user, \
                 patch("google.genai.Client") as mock_client_cls:

                mock_token.return_value = "valid-access-token"
                mock_user.return_value = self.mock_identity

                mock_client = MagicMock()
                mock_client.models.generate_content.return_value = resp_empty
                mock_client_cls.return_value = mock_client

                res = await run_agent(self.mock_db, self.user, "Hello")
                self.assertIn("Reached maximum steps", res["response"])

        asyncio.run(run_test())

    # ── Test F: Iteration limit enforcement ───────────────────────────────────
    def test_F_iteration_limit_enforced(self):
        async def run_test():
            fc = types.FunctionCall(name="get_projects", args={})
            infinite_resp = types.GenerateContentResponse(
                candidates=[types.Candidate(content=types.Content(role="model", parts=[types.Part(function_call=fc)]))]
            )

            with patch("app.services.agent_service.get_valid_access_token", new_callable=AsyncMock) as mock_token, \
                 patch("app.services.agent_service.fetch_current_jira_user", new_callable=AsyncMock) as mock_user, \
                 patch("app.services.agent_service._execute_tool", new_callable=AsyncMock) as mock_tool, \
                 patch("google.genai.Client") as mock_client_cls:

                mock_token.return_value = "valid-access-token"
                mock_user.return_value = self.mock_identity
                mock_tool.return_value = json.dumps({"projects": []})

                mock_client = MagicMock()
                mock_client.models.generate_content.return_value = infinite_resp
                mock_client_cls.return_value = mock_client

                res = await run_agent(self.mock_db, self.user, "Loop forever")

                self.assertEqual(res["iterations"], 10)
                self.assertEqual(mock_client.models.generate_content.call_count, 10)

        asyncio.run(run_test())

    # ── Test G: Self-healing cloud_id recovery regression ─────────────────────
    def test_G_self_healing_cloud_id_regression(self):
        async def run_test():
            from app.services.oauth_service import JiraResourceNotFoundError

            p = types.Part(text="Reconnected successfully.")
            resp = types.GenerateContentResponse(
                candidates=[types.Candidate(content=types.Content(role="model", parts=[p]))]
            )

            with patch("app.services.agent_service.get_valid_access_token", new_callable=AsyncMock) as mock_token, \
                 patch("app.services.agent_service.fetch_current_jira_user", new_callable=AsyncMock) as mock_user, \
                 patch("app.services.agent_service.fetch_cloud_id", new_callable=AsyncMock) as mock_fetch_cloud, \
                 patch("google.genai.Client") as mock_client_cls:

                mock_token.return_value = "valid-access-token"
                # First call fails with 404, second call succeeds with updated cloud ID
                mock_user.side_effect = [
                    JiraResourceNotFoundError("Site not found"),
                    self.mock_identity,
                ]
                mock_fetch_cloud.return_value = "new-active-cloud-id"

                mock_client = MagicMock()
                mock_client.models.generate_content.return_value = resp
                mock_client_cls.return_value = mock_client

                res = await run_agent(self.mock_db, self.user, "Show issues")

                self.assertEqual(self.conn.cloud_id, "new-active-cloud-id")
                self.mock_db.commit.assert_called()
                self.assertEqual(res["response"], "Reconnected successfully.")

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
