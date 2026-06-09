# 🤖 Jira AI Agent

> **Natural Language Jira Automation powered by Gemini AI, Atlassian OAuth 2.0, FastAPI, MCP, and PostgreSQL.**

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![Gemini](https://img.shields.io/badge/Gemini-2.5_Flash-orange?logo=google)](https://ai.google.dev)
[![Cloudflare](https://img.shields.io/badge/Cloudflare-Workers-F38020?logo=cloudflare)](https://workers.cloudflare.com/)
[![MCP](https://img.shields.io/badge/MCP-Protocol-purple)](https://modelcontextprotocol.io)
[![Atlassian OAuth](https://img.shields.io/badge/OAuth-2.0-blue?logo=atlassian)](https://developer.atlassian.com)
[![Render](https://img.shields.io/badge/Deploy-Render-46E3B7?logo=render)](https://render.com)
[![Neon](https://img.shields.io/badge/Database-Neon-00E599?logo=postgresql)](https://neon.tech)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue?logo=postgresql)](https://postgresql.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🌐 Live Demo

### 🚀 Live Application
https://zira-automation-agent.onrender.com

### 💻 Source Code
https://github.com/AnmolRajpoot25/Zira_automation_Agent

---
---

## ✨ Highlights

- 🤖 **AI-powered Jira Assistant** using Gemini 2.5 Flash-lite
- 🧠 **Conversational Memory** for contextual, multi-step workflows
- 🌍 **Global AI Access** via custom Cloudflare Edge Proxy to bypass region locks
- 🔐 **Secure Atlassian OAuth 2.0** Authentication
- ⚙️ **Agentic Tool Calling** with MCP Architecture
- 📋 **Natural Language** Issue Management
- 🗄️ **PostgreSQL Persistence** using Neon Serverless DB
- ⚡ **FastAPI Async Backend**
- 🔒 **Encrypted Token Storage** using Fernet
- ☁️ **Production Deployment** on Render

---

## 🎯 What This Does

Instead of clicking through Jira's UI, you can simply type instructions in plain English, and the agent remembers the context of your conversation:

| You Say | Agent Does |
|----------|------------|
| "Create a bug: login broken on mobile, High priority" | Creates issue with proper metadata (e.g., PROJ-42) |
| "Actually, assign it to me and make it Highest priority" | *Uses memory* to update PROJ-42 automatically |
| "Show all open bugs assigned to me" | Executes JQL search |
| "Add comment to MP-3: ready for code review" | Posts comment via Jira API |
| "What's the status of MP-10?" | Retrieves issue details |

The agent automatically determines:
- Which tools to call
- What arguments are required
- Which sequence of actions to perform
- How to translate natural language into Jira operations

---

## 🏗️ System Design

![System Design](assets/system-design.png)

### Architecture Overview

```text
User
 │
 ▼
Frontend (HTML/CSS/JS)
 │
 ▼
FastAPI Backend ◄──(Chat History & Context)──► Neon PostgreSQL
 │
 ├── Authentication Layer
 │     └── Atlassian OAuth 2.0
 │
 ├── Agent Orchestrator
 │     └── Cloudflare Worker (REST Proxy)
 │           └── Gemini 2.5 Flash
 │
 └── MCP Tool Layer
       ├── create_issue
       ├── update_issue
       ├── search_issues
       └── (Other Jira Tools)
               │
               ▼
          Jira REST API
```

---

## 🔄 Agent Workflow

```text
1. User Prompt
      │
      ▼
2. FastAPI Retrieves Chat History (Neon DB)
      │
      ▼
3. Request Routed via Cloudflare Proxy
      │
      ▼
4. Gemini Receives:
      - Past Conversation History
      - User Prompt
      - Tool Schemas
      - User Context
      │
      ▼
5. Gemini Chooses Tool(s)
      │
      ▼
6. MCP Tool Execution (Jira API)
      │
      ▼
7. Tool Response
      │
      ▼
8. Gemini Generates Final Answer
      │
      ▼
9. FastAPI Saves Response to DB & Returns to User
```

---

## 🛠️ Tech Stack

| Layer | Technology                   |
|---------|------------------------------|
| LLM | Gemini 2.5 Flash-lite        |
| Backend | FastAPI                      |
| Language | Python 3.11                  |
| Edge Proxy | Cloudflare Workers           |
| Database | PostgreSQL (Neon Serverless) |
| ORM | SQLAlchemy Async             |
| Authentication | Atlassian OAuth 2.0          |
| Agent Protocol | MCP                          |
| Security | Fernet Encryption            |
| Deployment | Render                       |
| Frontend | HTML, CSS, JavaScript        |
| HTTP Client | HTTPX                        |
| Migrations | Alembic                      |

---

## 🔐 Security Design

This project follows production-grade security practices:

### Authentication
- OAuth 2.0 Authorization Code Flow (3LO)
- State validation for CSRF protection
- Secure session handling

### Token Security
- OAuth tokens encrypted at rest
- Fernet encryption (AES + HMAC)
- No plaintext credentials stored

### User Isolation
- Per-user token storage and Chat History routing
- Identity-aware execution
- Complete credential separation

### Configuration Security
- Environment-variable driven configuration
- Startup validation via Pydantic
- No secrets hardcoded in source code

---

## 🛠️ Jira Tools Available

| Tool | Description |
|--------|------------|
| `get_current_user` | Fetch authenticated Jira user |
| `get_projects` | List available Jira projects |
| `get_issue` | Retrieve issue details |
| `search_issues` | Execute JQL search |
| `create_issue` | Create bug, task, or story |
| `update_issue` | Modify issue attributes |
| `delete_issue` | Delete issue |
| `add_comment` | Add issue comments |
| `get_transitions` | Retrieve valid workflow transitions |

---

## 📈 Project Metrics

- ✅ 10+ Jira Automation Tools
- ✅ OAuth 2.0 Integration
- ✅ Conversational DB Memory
- ✅ Edge Proxy API Routing
- ✅ MCP-Based Tool Architecture
- ✅ Production Cloud Deployment
- ✅ End-to-End AI Agent Workflow
- ✅ Multi-Step Function Calling
- ✅ Real Jira API Integration
- ✅ Secure Token Encryption

---

## 🚀 Local Setup

### Prerequisites

- Python 3.11+
- Atlassian Account
- Jira Project
- Gemini API Key
- Neon Database URL

### Installation

```bash
git clone [https://github.com/AnmolRajpoot25/Zira_automation_Agent.git](https://github.com/AnmolRajpoot25/Zira_automation_Agent.git)
cd Zira_automation_Agent
python -m venv .venv

# Activate Virtual Environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### Configure Environment

```bash
cp .env.example .env
```

Fill in your `.env` variables (ensure `DATABASE_URL` uses `postgresql+asyncpg://`):
```env
ATLASSIAN_CLIENT_ID=your_client_id
ATLASSIAN_CLIENT_SECRET=your_client_secret
ATLASSIAN_REDIRECT_URI=http://localhost:8000/auth/callback

GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash

JWT_SECRET=your_secret
ENCRYPTION_KEY=your_fernet_key

DATABASE_URL=postgresql+asyncpg://...

APP_ENV=development
FRONTEND_URL=http://localhost:8000
```

### Run Migrations & Start

```bash
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

---

## 🌐 Production Deployment (Render)

### Build Command
```bash
pip install -r requirements.txt
```

### Start Command
```bash
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

---

## 🗺️ Roadmap

- [ ] Multi-Agent Workflows
- [ ] Confluence Integration
- [ ] Slack Integration
- [ ] Streaming Responses
- [ ] Audit Logging Dashboard
- [ ] Multi-Tenant Jira Support
- [ ] Role-Based Access Control

---

## 🏆 Engineering Highlights

### Agentic AI Systems
- Multi-step tool-calling workflows
- Conversational memory state management
- Context-aware orchestration
- Identity-aware prompt injection

### Production Infrastructure
- Cloudflare Edge Proxy for API routing
- Render Web Services
- Neon Serverless PostgreSQL
- Alembic Database Migrations

### Backend Engineering
- FastAPI Async Architecture
- SQLAlchemy Async ORM
- Dependency Injection
- Modular Service Design

---

## 👨‍💻 Author

### Anmol Rajpoot
**B.Tech, Computer Science & Engineering** Indian Institute of Information Technology (IIIT) Bhopal

### Areas of Interest
- Agentic AI
- Generative AI
- LLM Applications
- Retrieval-Augmented Generation (RAG)
- Full-Stack AI Products

### Connect
GitHub: https://github.com/AnmolRajpoot25  
LinkedIn: https://www.linkedin.com/in/anmol-rajpoot/  

---

## 📄 License

MIT License  
Copyright (c) 2026 Anmol Rajpoot

⭐ If you found this project useful, consider giving it a star on GitHub.