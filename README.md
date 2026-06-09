# 🤖 Jira AI Agent
live Link "https://zira-automation-agent.onrender.com"
> **Natural language Jira automation** — talk to your project management tool like a human. Powered by **Google Gemini**, secured with **Atlassian OAuth 2.0**, built on **FastAPI + MCP**.

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![Gemini](https://img.shields.io/badge/Gemini-2.5_Flash-orange?logo=google)](https://ai.google.dev)
[![MCP](https://img.shields.io/badge/MCP-Protocol-purple)](https://modelcontextprotocol.io)
[![OAuth](https://img.shields.io/badge/OAuth-2.0_3LO-blue?logo=atlassian)](https://developer.atlassian.com)

---

## 🎯 What This Does

Instead of clicking through Jira's UI, you type natural language:

| You say | Agent does |
|---|---|
| *"Create a bug: login broken on mobile, High priority, due Friday"* | Creates issue with correct type, priority, due date |
| *"Assign MP-5 to me and move it to In Progress"* | Updates assignee + triggers status transition |
| *"Show all open bugs assigned to me"* | Runs JQL query, returns formatted results |
| *"Add comment to MP-3: ready for code review"* | Posts comment via Jira REST API |
| *"What's the status of MP-10?"* | Fetches full issue detail |

The agent figures out **which tools to call**, **in what order**, and **with what arguments** — all from a single sentence.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Phase 1 — OAuth 2.0 Login (Atlassian 3LO)                 │
│                                                              │
│  Client UI → Atlassian OAuth → Backend Orchestrator         │
│           → Encrypt tokens → Store in DB → Session set      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Phase 2 — Identity-Aware Agent Execution                   │
│                                                              │
│  User Prompt → Orchestrator → Inject user context           │
│             → Gemini (tool-use loop)                        │
│             → Jira REST API (signed with user token)        │
│             → Natural language response → UI                │
└─────────────────────────────────────────────────────────────┘
```

### Tech Stack

| Layer | Technology | Why |
|---|---|---|
| **LLM** | Google Gemini 2.5 Flash | Native function calling, free tier (1000 req/day) |
| **Backend** | FastAPI + Python 3.11 | Async-first, automatic OpenAPI docs |
| **Auth** | Atlassian OAuth 2.0 (3LO) | Industry-standard, per-user token isolation |
| **Agent Protocol** | MCP (Model Context Protocol) | Emerging standard for LLM tool use |
| **Database** | SQLite / PostgreSQL (SQLAlchemy async) | Encrypted token storage at rest |
| **Security** | Fernet encryption (AES-128-CBC + HMAC) | Tokens never stored in plaintext |
| **Frontend** | Vanilla JS + FastAPI static files | Zero-dependency, fully functional UI |

---

## 🔐 Security Design

This project was built with production security patterns from day one:

- **OAuth tokens encrypted at rest** using Fernet (AES-128-CBC + HMAC-SHA256) — raw tokens never touch the database
- **Per-user token isolation** — each agent run uses only that user's credentials, no cross-user token access possible
- **CSRF protection** via OAuth state parameter validation
- **Session cookies** are `HttpOnly`, `Secure` in production, `SameSite` configured per environment
- **No secrets in code** — all credentials via environment variables with Pydantic validation on startup

---

## 🛠️ Jira Tools Available

| Tool | Description |
|---|---|
| `get_current_user` | Returns logged-in user's accountId — used for "assign to me" |
| `get_projects` | Lists all accessible Jira projects |
| `get_issue` | Fetch full issue details by key |
| `search_issues` | JQL-powered search with up to 20 results |
| `create_issue` | Create tasks, bugs, stories with full metadata |
| `update_issue` | Update summary, assignee, priority, due date, labels, status |
| `delete_issue` | Permanently delete an issue |
| `add_comment` | Post a comment on any issue |
| `get_transitions` | List valid status transitions before changing status |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Atlassian account with a Jira project
- Google AI Studio account (free Gemini API key)

### 1. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/jira-ai-agent
cd jira-ai-agent
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
```

Fill in `.env`:

```env
# Atlassian OAuth — developer.atlassian.com/console/myapps/
ATLASSIAN_CLIENT_ID=your_client_id
ATLASSIAN_CLIENT_SECRET=your_client_secret
ATLASSIAN_REDIRECT_URI=http://localhost:8000/auth/callback

# Google Gemini — aistudio.google.com/app/apikey (free, no card needed)
GEMINI_API_KEY=your_gemini_key
GEMINI_MODEL=gemini-2.5-flash

# Generate these
SECRET_KEY=        # python -c "import secrets; print(secrets.token_hex(32))"
ENCRYPTION_KEY=    # python -m app.core.crypto

DATABASE_URL=sqlite+aiosqlite:///./jira_agent.db
APP_ENV=development
FRONTEND_URL=http://localhost:8000
```

### 3. Run

```bash
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000` → Login with Jira → Start chatting.

---

## 💬 Example Prompts

```
What projects do I have access to?
Show all open issues in project MP
Create a task in project MP: "Fix navbar bug" priority High due 2026-05-01 assign to me
Assign MP-3 to me and move it to In Progress
Add comment to MP-5: "Blocked by API rate limits, investigating"
Show all bugs assigned to me
Move MP-7 to Done
Set priority of MP-2 to Highest and due date to next Friday
Create a story: "User can reset password via email" in project MP
```

---

## 📁 Project Structure

```
jira-ai-agent/
├── app/
│   ├── core/
│   │   ├── config.py          # Pydantic settings — env var validation
│   │   ├── crypto.py          # Fernet token encryption at rest
│   │   └── database.py        # SQLAlchemy async engine
│   ├── models/
│   │   └── user.py            # User table — identity + encrypted tokens
│   ├── routers/
│   │   ├── auth.py            # OAuth flow: /login /callback /me /logout
│   │   └── agent.py           # POST /agent/chat — agent loop entry point
│   ├── services/
│   │   ├── oauth_service.py   # Phase 1: full OAuth 2.0 3LO flow
│   │   └── agent_service.py   # Phase 2: Gemini tool-use loop + Jira tools
│   └── main.py                # FastAPI app, middleware, startup
├── mcp_server/                # MCP server (Claude-compatible tool definitions)
├── frontend/
│   └── index.html             # Chat UI — login + agent interface
├── requirements.txt
└── .env.example
```

---

## 🔄 Agent Loop (How It Works)

```
1. User sends: "Assign MP-5 to me and move to In Progress"

2. Gemini receives prompt + tool schemas + system prompt with user context
   (system prompt includes: "User is Anmol Rajput, accountId: 712020:...")

3. Gemini decides: call get_current_user → then update_issue

4. Tool call 1: get_current_user()
   → returns { accountId: "712020:5c7d...", displayName: "Anmol Rajput" }

5. Tool call 2: update_issue(issue_key="MP-5", assignee_account_id="712020:5c7d...", status_transition_name="In Progress")
   → calls Jira REST API with user's OAuth token
   → returns { success: true }

6. Gemini generates: "Done! MP-5 is now assigned to you and moved to In Progress."

7. Response shown in UI. Total: 2 iterations, ~1.2s.
```

---

## 🌐 Deployment

### Railway (recommended)

```bash
# 1. Push to GitHub
git add . && git commit -m "deploy" && git push

# 2. railway.app → New Project → Deploy from GitHub

# 3. Add environment variables in Railway dashboard

# 4. Update Atlassian callback URL to:
#    https://YOUR-APP.railway.app/auth/callback
```

### Environment variables for production

```env
APP_ENV=production
FRONTEND_URL=https://YOUR-APP.railway.app
ATLASSIAN_REDIRECT_URI=https://YOUR-APP.railway.app/auth/callback
DATABASE_URL=sqlite+aiosqlite:///./jira_agent.db
```

---

## 🗺️ Roadmap

- [ ] PostgreSQL support for production persistence
- [ ] Multi-site Jira support (site picker on login)
- [ ] Streaming responses (Server-Sent Events)
- [ ] Confluence integration (create/update pages)
- [ ] Slack notification on issue updates
- [ ] Claude model support (swap back via env var)
- [ ] Rate limiting per user
- [ ] Audit log of all agent actions

---

## 🧠 What I Learned Building This

- **OAuth 2.0 three-legged flow** in production — state validation, token exchange, refresh token rotation
- **Agentic AI patterns** — multi-step tool-use loops, system prompt injection, identity-aware context
- **MCP (Model Context Protocol)** — the emerging standard for connecting LLMs to external tools
- **Async Python at scale** — SQLAlchemy async, httpx async, FastAPI dependency injection
- **Security engineering** — encryption at rest, per-user credential isolation, CSRF protection

---

## 👨‍💻 Author

**Anmol Rajput**
- Built as a portfolio project demonstrating production AI engineering patterns
- Combines OAuth security, agentic AI, and real-world API integration in one system

---

## 📄 License

MIT — free to use, modify, and deploy.
