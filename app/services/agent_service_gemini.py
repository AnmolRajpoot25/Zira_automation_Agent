"""
Phase 2: Identity-aware agent execution — Gemini version.

Drop-in replacement for agent_service.py (Claude).
Only this file changes — everything else (MCP server, OAuth, DB) stays identical.

Install: pip install google-genai
"""
import json
from sqlalchemy.ext.asyncio import AsyncSession
from google import genai
from google.genai import types

from app.core.config import get_settings
from app.models.user import User
from app.services.oauth_service import get_valid_access_token
from mcp import ClientSession
from mcp.client.stdio import stdio_client
from mcp import StdioServerParameters

settings = get_settings()

# ── Gemini client ────────────────────────────────────────────────────────────
gemini_client = genai.Client(api_key=settings.gemini_api_key)

GEMINI_MODEL = "gemini-2.5-flash"   # free tier — 1000 req/day
MAX_ITERATIONS = 10


def _build_system_prompt(user: User) -> str:
    return f"""You are a Jira assistant helping {user.display_name}.

User context:
- Name: {user.display_name}
- Email: {user.email}
- Jira accountId: {user.account_id}
- Jira site: {user.jira_base_url}

Guidelines:
- When the user says "me", "myself", use accountId {user.account_id}.
- Confirm each action clearly and concisely.
- Never expose raw JSON, token values, or internal IDs in your response.
- Keep responses to 1-3 sentences unless detail is requested.
"""


def _mcp_tools_to_gemini(mcp_tools) -> list[types.Tool]:
    """Convert MCP tool definitions → Gemini FunctionDeclaration format."""
    declarations = []
    for t in mcp_tools.tools:
        schema = t.inputSchema or {}
        # Gemini requires properties to exist even if empty
        if "properties" not in schema:
            schema["properties"] = {}
        declarations.append(
            types.FunctionDeclaration(
                name=t.name,
                description=t.description or "",
                parameters=schema,
            )
        )
    return [types.Tool(function_declarations=declarations)]


async def run_agent(
    db: AsyncSession,
    user: User,
    user_prompt: str,
) -> dict:
    """
    Run the full agent loop for a single user prompt using Gemini.

    Returns:
        {
          "response": str,
          "tool_calls": list[dict],
          "iterations": int,
        }
    """
    access_token = await get_valid_access_token(db, user)

    server_params = StdioServerParameters(
        command="python",
        args=["-m", "mcp_server.run_server"],
        env={
            "ACCESS_TOKEN": access_token,
            "CLOUD_ID": user.cloud_id,
            "ACCOUNT_ID": user.account_id,
            "DISPLAY_NAME": user.display_name,
        },
    )

    tool_call_log: list[dict] = []
    system_prompt = _build_system_prompt(user)

    # Gemini uses a flat contents list (no separate system role in history)
    contents: list[types.Content] = [
        types.Content(
            role="user",
            parts=[types.Part(text=user_prompt)],
        )
    ]

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as mcp_session:
            await mcp_session.initialize()

            mcp_tools = await mcp_session.list_tools()
            gemini_tools = _mcp_tools_to_gemini(mcp_tools)

            config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                tools=gemini_tools,
                temperature=0.1,  # lower = more deterministic tool use
            )

            for iteration in range(MAX_ITERATIONS):
                response = gemini_client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=contents,
                    config=config,
                )

                candidate = response.candidates[0]
                contents.append(
                    types.Content(role="model", parts=candidate.content.parts)
                )

                # Collect function calls from this response
                function_calls = [
                    p.function_call
                    for p in candidate.content.parts
                    if p.function_call is not None
                ]

                # If no function calls → Claude is done
                if not function_calls:
                    final_text = "".join(
                        p.text for p in candidate.content.parts if p.text
                    )
                    return {
                        "response": final_text,
                        "tool_calls": tool_call_log,
                        "iterations": iteration + 1,
                    }

                # Execute each function call via MCP
                function_responses = []
                for fc in function_calls:
                    tool_call_log.append({
                        "tool": fc.name,
                        "input": dict(fc.args),
                    })

                    try:
                        result = await mcp_session.call_tool(
                            fc.name, dict(fc.args)
                        )
                        content = result.content[0].text if result.content else "{}"
                        tool_call_log[-1]["result"] = "success"
                    except Exception as exc:
                        content = json.dumps({"error": str(exc)})
                        tool_call_log[-1]["result"] = f"error: {exc}"

                    function_responses.append(
                        types.Part(
                            function_response=types.FunctionResponse(
                                name=fc.name,
                                response={"result": content},
                            )
                        )
                    )

                # Feed tool results back into the conversation
                contents.append(
                    types.Content(role="user", parts=function_responses)
                )

    return {
        "response": "Reached max steps. Please try a more specific request.",
        "tool_calls": tool_call_log,
        "iterations": MAX_ITERATIONS,
    }
