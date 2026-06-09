import json
import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration, Tool, GenerationConfig

from app.core.config import get_settings
from app.core.crypto import decrypt_value
from app.models.user import JiraConnection, User
from app.services.oauth_service import fetch_current_jira_user, get_valid_access_token

settings = get_settings()

MAX_ITERATIONS = 10


def _build_system_prompt(user: User, jira_identity: dict, cloud_id: str) -> str:
    jira_name = jira_identity.get("displayName") or user.name
    account_id = jira_identity["accountId"]
    return f"""You are a Jira assistant helping {jira_name}.

User context:
- App user: {user.name}
- Email: {user.email}
- Jira accountId: {account_id}
- Jira cloudId: {cloud_id}

Guidelines:
- When the user says "me", "myself", or "assign to me", use accountId {account_id}.
- Always confirm the action you took in a clear, friendly sentence.
- If a tool call fails, explain what went wrong and suggest alternatives.
- Keep responses concise unless detail is requested.
- Never expose raw JSON, token values, or internal IDs in your response.
- For creating issues, always ask for project key if not provided.
- Due dates should be in YYYY-MM-DD format.
"""


async def _jira_call(method, path, access_token, cloud_id, **kwargs):
    base = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(headers=headers, timeout=20) as client:
        resp = await getattr(client, method)(f"{base}{path}", **kwargs)
        resp.raise_for_status()
        return resp.json() if resp.content else {}


async def _execute_tool(name, args, access_token, cloud_id, account_id, display_name):
    try:
        if name == "get_current_user":
            return json.dumps({"accountId": account_id, "displayName": display_name})

        elif name == "get_issue":
            data = await _jira_call("get", f"/issue/{args['issue_key']}", access_token, cloud_id)
            fields = data.get("fields", {})
            return json.dumps({
                "key": data["key"],
                "summary": fields.get("summary"),
                "status": fields.get("status", {}).get("name"),
                "assignee": (fields.get("assignee") or {}).get("displayName"),
                "description": fields.get("description"),
                "priority": (fields.get("priority") or {}).get("name"),
                "due_date": fields.get("duedate"),
                "issue_type": fields.get("issuetype", {}).get("name"),
                "reporter": (fields.get("reporter") or {}).get("displayName"),
            })

        elif name == "search_issues":
            max_r = min(args.get("max_results", 10), 20)
            data = await _jira_call(
                "get", "/search", access_token, cloud_id,
                params={"jql": args["jql"], "maxResults": max_r,
                        "fields": "summary,status,assignee,priority,duedate,issuetype"},
            )
            return json.dumps([
                {
                    "key": i["key"],
                    "summary": i["fields"].get("summary"),
                    "status": i["fields"].get("status", {}).get("name"),
                    "assignee": (i["fields"].get("assignee") or {}).get("displayName"),
                    "priority": (i["fields"].get("priority") or {}).get("name"),
                    "due_date": i["fields"].get("duedate"),
                    "issue_type": i["fields"].get("issuetype", {}).get("name"),
                }
                for i in data.get("issues", [])
            ])

        elif name == "create_issue":
            project_key = args["project_key"]
            summary = args["summary"]
            issue_type = args.get("issue_type", "Task")
            
            payload = {
                "fields": {
                    "project": {"key": project_key},
                    "summary": summary,
                    "issuetype": {"name": issue_type},
                }
            }
            
            if "description" in args:
                payload["fields"]["description"] = {
                    "type": "doc", "version": 1,
                    "content": [{"type": "paragraph", "content": [
                        {"type": "text", "text": args["description"]}
                    ]}],
                }
            if "assignee_account_id" in args:
                payload["fields"]["assignee"] = {"accountId": args["assignee_account_id"]}
            if "priority" in args:
                payload["fields"]["priority"] = {"name": args["priority"]}
            if "due_date" in args:
                payload["fields"]["duedate"] = args["due_date"]
            if "labels" in args:
                payload["fields"]["labels"] = args["labels"]

            data = await _jira_call("post", "/issue", access_token, cloud_id, json=payload)
            return json.dumps({
                "success": True,
                "issue_key": data.get("key"),
                "issue_id": data.get("id"),
                "message": f"Issue {data.get('key')} created successfully.",
            })

        elif name == "update_issue":
            key = args["issue_key"]
            payload: dict = {"fields": {}}

            if "summary" in args:
                payload["fields"]["summary"] = args["summary"]
            if "description" in args:
                payload["fields"]["description"] = {
                    "type": "doc", "version": 1,
                    "content": [{"type": "paragraph", "content": [
                        {"type": "text", "text": args["description"]}
                    ]}],
                }
            if "assignee_account_id" in args:
                payload["fields"]["assignee"] = {"accountId": args["assignee_account_id"]}
            if "priority" in args:
                payload["fields"]["priority"] = {"name": args["priority"]}
            if "due_date" in args:
                payload["fields"]["duedate"] = args["due_date"]
            if "labels" in args:
                payload["fields"]["labels"] = args["labels"]

            if payload["fields"]:
                await _jira_call("put", f"/issue/{key}", access_token, cloud_id, json=payload)

            if "status_transition_name" in args:
                trans = await _jira_call("get", f"/issue/{key}/transitions", access_token, cloud_id)
                target = next(
                    (t for t in trans.get("transitions", [])
                     if t["name"].lower() == args["status_transition_name"].lower()), None
                )
                if target:
                    await _jira_call("post", f"/issue/{key}/transitions", access_token, cloud_id,
                                     json={"transition": {"id": target["id"]}})
                else:
                    available = [t["name"] for t in trans.get("transitions", [])]
                    return json.dumps({"error": "Transition not found.", "available": available})

            return json.dumps({"success": True, "issue_key": key, "message": f"Issue {key} updated."})

        elif name == "delete_issue":
            key = args["issue_key"]
            await _jira_call("delete", f"/issue/{key}", access_token, cloud_id)
            return json.dumps({"success": True, "message": f"Issue {key} deleted."})

        elif name == "add_comment":
            key = args["issue_key"]
            data = await _jira_call("post", f"/issue/{key}/comment", access_token, cloud_id,
                json={"body": {
                    "type": "doc", "version": 1,
                    "content": [{"type": "paragraph", "content": [
                        {"type": "text", "text": args["body"]}
                    ]}],
                }})
            return json.dumps({"success": True, "comment_id": data.get("id")})

        elif name == "get_transitions":
            data = await _jira_call("get", f"/issue/{args['issue_key']}/transitions", access_token, cloud_id)
            transitions = [{"id": t["id"], "name": t["name"]} for t in data.get("transitions", [])]
            return json.dumps({"transitions": transitions})

        elif name == "get_projects":
            data = await _jira_call("get", "/project", access_token, cloud_id)
            projects = [{"key": p["key"], "name": p["name"], "id": p["id"]} for p in data]
            return json.dumps({"projects": projects})

        else:
            return json.dumps({"error": f"Unknown tool: {name}"})

    except Exception as exc:
        return json.dumps({"error": str(exc)})


def _build_gemini_tools(account_id, display_name):
    return [Tool(function_declarations=[
        FunctionDeclaration(
            name="get_current_user",
            description=f"Returns current user profile. accountId={account_id}, displayName={display_name}. Use when user says 'me', 'myself', or 'I'.",
            parameters={"type": "object", "properties": {}},
        ),
        FunctionDeclaration(
            name="get_projects",
            description="Get all Jira projects the user has access to. Use this to find project keys before creating issues.",
            parameters={"type": "object", "properties": {}},
        ),
        FunctionDeclaration(
            name="get_issue",
            description="Fetch a Jira issue by its key (e.g. PROJ-123). Returns full details.",
            parameters={
                "type": "object",
                "properties": {
                    "issue_key": {"type": "string", "description": "Jira issue key e.g. PROJ-42"},
                },
                "required": ["issue_key"],
            },
        ),
        FunctionDeclaration(
            name="search_issues",
            description="Search Jira issues using JQL. Returns up to 20 results. Use for listing, filtering, finding issues.",
            parameters={
                "type": "object",
                "properties": {
                    "jql": {"type": "string", "description": "JQL query. Examples: 'project=PROJ AND status=Open', 'assignee=currentUser()', 'created>=-7d'"},
                    "max_results": {"type": "integer", "description": "Max results 1-20, default 10"},
                },
                "required": ["jql"],
            },
        ),
        FunctionDeclaration(
            name="create_issue",
            description="Create a new Jira issue/task/bug/story. Must have project_key and summary.",
            parameters={
                "type": "object",
                "properties": {
                    "project_key": {"type": "string", "description": "Project key e.g. PROJ, DEV, TEST"},
                    "summary": {"type": "string", "description": "Issue title/summary"},
                    "issue_type": {"type": "string", "description": "Task, Bug, Story, Epic. Default: Task"},
                    "description": {"type": "string", "description": "Detailed description"},
                    "assignee_account_id": {"type": "string", "description": "accountId of assignee"},
                    "priority": {"type": "string", "description": "Highest, High, Medium, Low, Lowest"},
                    "due_date": {"type": "string", "description": "Due date in YYYY-MM-DD format"},
                    "labels": {"type": "array", "items": {"type": "string"}, "description": "List of labels"},
                },
                "required": ["project_key", "summary"],
            },
        ),
        FunctionDeclaration(
            name="update_issue",
            description="Update an existing Jira issue. Only provide fields you want to change.",
            parameters={
                "type": "object",
                "properties": {
                    "issue_key": {"type": "string"},
                    "summary": {"type": "string"},
                    "description": {"type": "string"},
                    "assignee_account_id": {"type": "string"},
                    "priority": {"type": "string", "description": "Highest, High, Medium, Low, Lowest"},
                    "due_date": {"type": "string", "description": "YYYY-MM-DD format"},
                    "labels": {"type": "array", "items": {"type": "string"}},
                    "status_transition_name": {"type": "string", "description": "e.g. 'In Progress', 'Done', 'To Do'"},
                },
                "required": ["issue_key"],
            },
        ),
        FunctionDeclaration(
            name="delete_issue",
            description="Delete a Jira issue permanently. Use with caution.",
            parameters={
                "type": "object",
                "properties": {
                    "issue_key": {"type": "string", "description": "Issue key to delete e.g. PROJ-42"},
                },
                "required": ["issue_key"],
            },
        ),
        FunctionDeclaration(
            name="add_comment",
            description="Add a comment to a Jira issue.",
            parameters={
                "type": "object",
                "properties": {
                    "issue_key": {"type": "string"},
                    "body": {"type": "string", "description": "Comment text"},
                },
                "required": ["issue_key", "body"],
            },
        ),
        FunctionDeclaration(
            name="get_transitions",
            description="Get available status transitions for an issue. Use before changing status to know valid options.",
            parameters={
                "type": "object",
                "properties": {
                    "issue_key": {"type": "string"},
                },
                "required": ["issue_key"],
            },
        ),
    ])]


async def run_agent(db: AsyncSession, user: User, user_prompt: str) -> dict:
    result = await db.execute(
        select(JiraConnection).where(JiraConnection.user_id == user.id)
    )
    connection = result.scalar_one_or_none()
    if connection is None:
        raise HTTPException(status_code=400, detail="Connect Jira before using the agent.")

    gemini_api_key = decrypt_value(user.encrypted_gemini_key)
    if gemini_api_key is None:
        raise HTTPException(status_code=400, detail="Add your Gemini API key in settings first.")

    access_token = await get_valid_access_token(db, connection)
    jira_identity = await fetch_current_jira_user(access_token, connection.cloud_id)
    jira_account_id = jira_identity["accountId"]
    jira_display_name = jira_identity.get("displayName") or user.name

    genai.configure(api_key=gemini_api_key)
    system_prompt = _build_system_prompt(user, jira_identity, connection.cloud_id)
    tools = _build_gemini_tools(jira_account_id, jira_display_name)

    model = genai.GenerativeModel(
        model_name=settings.gemini_model,
        system_instruction=system_prompt,
        tools=tools,
        generation_config=GenerationConfig(temperature=0.2, max_output_tokens=2048),
    )

    chat = model.start_chat(history=[])
    tool_call_log: list[dict] = []
    final_text = ""
    response = await chat.send_message_async(user_prompt)

    import google.generativeai.protos as protos

    for _ in range(MAX_ITERATIONS):
        parts = response.candidates[0].content.parts
        function_calls = [p for p in parts if hasattr(p, "function_call") and p.function_call.name]
        text_parts = [p.text for p in parts if hasattr(p, "text") and p.text]

        if text_parts:
            final_text = " ".join(text_parts)

        if not function_calls:
            return {
                "response": final_text,
                "tool_calls": tool_call_log,
                "iterations": _ + 1,
            }

        tool_response_parts = []
        for fc in function_calls:
            fn_name = fc.function_call.name
            fn_args = dict(fc.function_call.args)
            tool_call_log.append({"tool": fn_name, "input": fn_args})

            result_str = await _execute_tool(
                fn_name, fn_args,
                access_token, connection.cloud_id,
                jira_account_id, jira_display_name,
            )
            result_data = json.loads(result_str)
            tool_call_log[-1]["result"] = "success" if "error" not in result_data else result_data["error"]

            tool_response_parts.append(
                protos.Part(
                    function_response=protos.FunctionResponse(
                        name=fn_name,
                        response={"result": result_data},
                    )
                )
            )

        response = await chat.send_message_async(tool_response_parts)

    return {
        "response": final_text or "Reached maximum steps. Please try a more specific request.",
        "tool_calls": tool_call_log,
        "iterations": MAX_ITERATIONS,
    }
