"""
User-specific MCP server.

Each agent run instantiates this with the user's OAuth token so every
Jira API call is automatically signed for the correct user.

Tools exposed:
  - get_issue        : fetch a Jira issue by key
  - search_issues    : JQL search
  - update_issue     : patch summary / description / assignee / status
  - add_comment      : post a comment on an issue
  - get_current_user : return the token owner's profile (useful for "assign to me")
"""
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import json


def create_jira_mcp_server(
    access_token: str,
    cloud_id: str,
    account_id: str,
    display_name: str,
) -> Server:
    server = Server("jira-agent")
    base = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    # ── Tool definitions ─────────────────────────────────────────────────────

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="get_current_user",
                description=(
                    f"Returns the current user's Jira profile. "
                    f"accountId={account_id}, displayName={display_name}. "
                    "Use this whenever the user says 'me', 'myself', or 'I'."
                ),
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            Tool(
                name="get_issue",
                description="Fetch a Jira issue by its key (e.g. PROJ-123).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "issue_key": {
                            "type": "string",
                            "description": "Jira issue key, e.g. PROJ-42",
                        }
                    },
                    "required": ["issue_key"],
                },
            ),
            Tool(
                name="search_issues",
                description="Search Jira issues using JQL. Returns up to 20 results.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "jql": {
                            "type": "string",
                            "description": "JQL query string",
                        },
                        "max_results": {
                            "type": "integer",
                            "default": 10,
                            "description": "Max results to return (1–20)",
                        },
                    },
                    "required": ["jql"],
                },
            ),
            Tool(
                name="update_issue",
                description=(
                    "Update a Jira issue. Provide only the fields you want to change. "
                    "To assign to the current user, set assignee_account_id to the value "
                    "returned by get_current_user."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "issue_key": {"type": "string"},
                        "summary": {"type": "string"},
                        "description": {"type": "string"},
                        "assignee_account_id": {
                            "type": "string",
                            "description": "accountId of the assignee",
                        },
                        "status_transition_name": {
                            "type": "string",
                            "description": "Transition name, e.g. 'In Progress', 'Done'",
                        },
                    },
                    "required": ["issue_key"],
                },
            ),
            Tool(
                name="add_comment",
                description="Add a comment to a Jira issue.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "issue_key": {"type": "string"},
                        "body": {"type": "string", "description": "Comment text"},
                    },
                    "required": ["issue_key", "body"],
                },
            ),
        ]

    # ── Tool implementations ─────────────────────────────────────────────────

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        async with httpx.AsyncClient(headers=headers, timeout=20) as client:

            if name == "get_current_user":
                return [TextContent(type="text", text=json.dumps({
                    "accountId": account_id,
                    "displayName": display_name,
                }))]

            elif name == "get_issue":
                key = arguments["issue_key"]
                resp = await client.get(f"{base}/issue/{key}")
                resp.raise_for_status()
                data = resp.json()
                fields = data.get("fields", {})
                return [TextContent(type="text", text=json.dumps({
                    "key": data["key"],
                    "summary": fields.get("summary"),
                    "status": fields.get("status", {}).get("name"),
                    "assignee": (fields.get("assignee") or {}).get("displayName"),
                    "description": fields.get("description"),
                    "priority": (fields.get("priority") or {}).get("name"),
                }))]

            elif name == "search_issues":
                jql = arguments["jql"]
                max_r = min(arguments.get("max_results", 10), 20)
                resp = await client.get(
                    f"{base}/search",
                    params={"jql": jql, "maxResults": max_r,
                            "fields": "summary,status,assignee,priority"},
                )
                resp.raise_for_status()
                issues = [
                    {
                        "key": i["key"],
                        "summary": i["fields"].get("summary"),
                        "status": i["fields"].get("status", {}).get("name"),
                        "assignee": (i["fields"].get("assignee") or {}).get("displayName"),
                    }
                    for i in resp.json().get("issues", [])
                ]
                return [TextContent(type="text", text=json.dumps(issues))]

            elif name == "update_issue":
                key = arguments["issue_key"]
                update_payload: dict = {"fields": {}}

                if "summary" in arguments:
                    update_payload["fields"]["summary"] = arguments["summary"]

                if "description" in arguments:
                    update_payload["fields"]["description"] = {
                        "type": "doc",
                        "version": 1,
                        "content": [{
                            "type": "paragraph",
                            "content": [{"type": "text", "text": arguments["description"]}],
                        }],
                    }

                if "assignee_account_id" in arguments:
                    update_payload["fields"]["assignee"] = {
                        "accountId": arguments["assignee_account_id"]
                    }

                # Apply field updates
                if update_payload["fields"]:
                    resp = await client.put(f"{base}/issue/{key}", json=update_payload)
                    resp.raise_for_status()

                # Handle status transition separately
                if "status_transition_name" in arguments:
                    trans_resp = await client.get(f"{base}/issue/{key}/transitions")
                    trans_resp.raise_for_status()
                    transitions = trans_resp.json().get("transitions", [])
                    target = next(
                        (t for t in transitions
                         if t["name"].lower() == arguments["status_transition_name"].lower()),
                        None,
                    )
                    if target:
                        await client.post(
                            f"{base}/issue/{key}/transitions",
                            json={"transition": {"id": target["id"]}},
                        )
                    else:
                        available = [t["name"] for t in transitions]
                        return [TextContent(type="text", text=json.dumps({
                            "error": f"Transition '{arguments['status_transition_name']}' not found.",
                            "available_transitions": available,
                        }))]

                return [TextContent(type="text", text=json.dumps({
                    "success": True,
                    "issue_key": key,
                    "message": f"Issue {key} updated successfully.",
                }))]

            elif name == "add_comment":
                key = arguments["issue_key"]
                resp = await client.post(
                    f"{base}/issue/{key}/comment",
                    json={
                        "body": {
                            "type": "doc",
                            "version": 1,
                            "content": [{
                                "type": "paragraph",
                                "content": [{"type": "text", "text": arguments["body"]}],
                            }],
                        }
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return [TextContent(type="text", text=json.dumps({
                    "success": True,
                    "comment_id": data.get("id"),
                }))]

            else:
                return [TextContent(type="text", text=json.dumps({
                    "error": f"Unknown tool: {name}"
                }))]

    return server
