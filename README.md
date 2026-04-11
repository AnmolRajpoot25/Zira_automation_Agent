# Jira AI Agent

Natural language Jira automation powered by **Claude** (Anthropic) + **MCP** (Model Context Protocol), with full **Atlassian OAuth 2.0** authentication.

---

## Architecture

```
Phase 1 — OAuth Login
  Client UI → Atlassian OAuth → Backend Orchestrator → DB (encrypted tokens)

Phase 2 — Agent Execution
  Client UI → Orchestrator → [inject user context]
            → User-specific MCP Server → Claude tool-use loop → Jira API
            → Natural language response → Client UI
```

---

## Project Structure

```
jira-agent/
├── app/
│   ├── core/
│   │   ├── config.py        # Pydantic settings (env vars)
│   │   ├── crypto.py        # Fernet token encryption at rest
│   │   └── database.py      # SQLAlchemy async engine + session
│   ├── models/
│   │   └── user.py          # User table (identity + encrypted tokens)
│   ├── routers/
│   │   ├── auth.py          # GET /auth/login, /auth/callback, /auth/me
│   │   └── agent.py         # POST /agent/chat
│   ├── services/
│   │   ├── oauth_service.py # Phase 1: full OAuth flow + token refresh
│   │   └── agent_service.py # Phase 2: Claude tool-use loop
│   └── main.py              # FastAPI app, middleware, lifecycle
├── mcp_server/
│   ├── jira_mcp.py          # MCP server: Jira tools (get/search/update/comment)
│   └── run_server.py        # Subprocess entrypoint (one instance per agent run)
├── frontend/
│   └── index.html           # Minimal test UI (login + chat)
├── requirements.txt
└── .env.example
```

---

## Quick Start

### 1. Clone and install

```bash
git clone <your-repo>
cd jira-agent
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Create an Atlassian OAuth app

1. Go to https://developer.atlassian.com/console/myapps/
2. Click **Create** → **OAuth 2.0 integration**
3. Under **Permissions**, add:
   - Jira API → `read:jira-work`, `write:jira-work`, `read:jira-user`
4. Under **Authorization**, set callback URL:
   ```
   http://localhost:8000/auth/callback
   ```
5. Copy **Client ID** and **Client Secret**

### 3. Configure environment

```bash
cp .env .env
```

Edit `.env`:

```env
ATLASSIAN_CLIENT_ID=<your client id>
ATLASSIAN_CLIENT_SECRET=<your client secret>
ATLASSIAN_REDIRECT_URI=http://localhost:8000/auth/callback
GEMINI_API_KEY=<your gemini key>  # free at aistudio.google.com

# Generate these:
SECRET_KEY=<run: python -c "import secrets; print(secrets.token_hex(32))">
ENCRYPTION_KEY=<run: python -m app.core.crypto>
```

### 4. Run

```bash
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000 in your browser.

---

## Usage

### Login
Click **Login with Jira** → authorize on Atlassian → redirected back, now authenticated.

### Chat examples

| Prompt | What happens |
|---|---|
| `Assign PROJ-42 to me` | Fetches your accountId, calls `update_issue` |
| `Show me all open bugs in project MYAPP` | Calls `search_issues` with JQL |
| `Add a comment to PROJ-10: ready for review` | Calls `add_comment` |
| `Move PROJ-5 to In Progress` | Calls `update_issue` with status transition |
| `What's the status of PROJ-99?` | Calls `get_issue` |

---

## API Reference

### Auth

| Method | Path | Description |
|---|---|---|
| `GET` | `/auth/login` | Redirect to Atlassian OAuth |
| `GET` | `/auth/callback` | OAuth callback — sets session cookie |
| `GET` | `/auth/me` | Current user profile |
| `POST` | `/auth/logout` | Clear session |

### Agent

| Method | Path | Body | Description |
|---|---|---|---|
| `POST` | `/agent/chat` | `{"prompt": "..."}` | Run agent loop, return response |

### Response shape

```json
{
  "response": "Done! PROJ-42 is now assigned to you.",
  "tool_calls": [
    {"tool": "get_current_user", "input": {}, "result": "success"},
    {"tool": "update_issue", "input": {"issue_key": "PROJ-42", "assignee_account_id": "..."}, "result": "success"}
  ],
  "iterations": 2
}
```

---

## MCP Tools Available to Claude

| Tool | Description |
|---|---|
| `get_current_user` | Returns the logged-in user's accountId + displayName |
| `get_issue` | Fetch issue by key (summary, status, assignee, description) |
| `search_issues` | JQL search, returns up to 20 results |
| `update_issue` | Update summary, description, assignee, or status transition |
| `add_comment` | Post a comment on an issue |

---

## Security Notes

- **Tokens are encrypted at rest** using Fernet (AES-128-CBC + HMAC-SHA256)
- **Each agent run** spawns an isolated MCP server subprocess with only that user's token — no cross-user token access possible
- **CSRF protection** via state parameter checked on OAuth callback
- **Session cookie** is `HttpOnly`, `SameSite=lax`, `Secure` in production
- In production: use PostgreSQL, set `APP_ENV=production`, and put the app behind HTTPS

---

## Extending

### Add a new Jira tool

In `mcp_server/jira_mcp.py`, add an entry to `list_tools()` and a branch in `call_tool()`.

### Add more OAuth scopes

Update `oauth_scopes` in `app/core/config.py` and re-authorize.

### Multi-site support

`oauth_service.fetch_user_identity()` currently picks the first accessible site. Replace with a site-picker UI and store the chosen `cloud_id` per user.
