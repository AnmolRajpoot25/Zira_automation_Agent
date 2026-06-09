# 🤖 Jira AI Agent

> **Natural Language Jira Automation powered by Gemini AI, Atlassian OAuth 2.0, FastAPI, MCP, and PostgreSQL.**

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![Gemini](https://img.shields.io/badge/Gemini-2.5_Flash-orange?logo=google)](https://ai.google.dev)
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

https://github.com/AnmolRajpoot25/jira-ai-agent

---

## 🎥 Demo

> Add a GIF or short demo video here.

```md
![Demo](assets/demo.gif)
```

---

## ✨ Highlights

- 🤖 AI-powered Jira Assistant using Gemini 2.5 Flash
- 🔐 Secure Atlassian OAuth 2.0 Authentication
- 🧠 Agentic Tool Calling with MCP Architecture
- 📋 Natural Language Issue Management
- 🗄️ PostgreSQL Persistence using Neon
- ⚡ FastAPI Async Backend
- 🔒 Encrypted Token Storage using Fernet
- ☁️ Production Deployment on Render
- 🔄 Multi-step Function Calling
- 🚀 Production-ready Architecture

---

## 🎯 What This Does

Instead of clicking through Jira's UI, you can simply type instructions in plain English:

| You Say | Agent Does |
|----------|------------|
| "Create a bug: login broken on mobile, High priority, due Friday" | Creates issue with proper metadata |
| "Assign MP-5 to me and move it to In Progress" | Updates assignee and workflow status |
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
FastAPI Backend
 │
 ├── Authentication Layer
 │     └── Atlassian OAuth 2.0
 │
 ├── Agent Orchestrator
 │     └── Gemini 2.5 Flash
 │
 ├── MCP Tool Layer
 │     ├── create_issue
 │     ├── update_issue
 │     ├── search_issues
 │     ├── add_comment
 │     └── get_issue
 │
 └── Database Layer
       └── Neon PostgreSQL

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
2. FastAPI Agent Endpoint
      │
      ▼
3. Gemini Receives:
      - User Prompt
      - Tool Schemas
      - User Context
      │
      ▼
4. Gemini Chooses Tool(s)
      │
      ▼
5. MCP Tool Execution
      │
      ▼
6. Jira REST API
      │
      ▼
7. Tool Response
      │
      ▼
8. Gemini Generates Final Answer
      │
      ▼
9. User Receives Response
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---------|------------|
| LLM | Gemini 2.5 Flash |
| Backend | FastAPI |
| Language | Python 3.11 |
| Database | PostgreSQL (Neon) |
| ORM | SQLAlchemy Async |
| Authentication | Atlassian OAuth 2.0 |
| Agent Protocol | MCP |
| Security | Fernet Encryption |
| Deployment | Render |
| Frontend | HTML, CSS, JavaScript |
| HTTP Client | HTTPX |
| Migrations | Alembic |

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
- Per-user token storage
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
| get_current_user | Fetch authenticated Jira user |
| get_projects | List available Jira projects |
| get_issue | Retrieve issue details |
| search_issues | Execute JQL search |
| create_issue | Create bug, task, or story |
| update_issue | Modify issue attributes |
| delete_issue | Delete issue |
| add_comment | Add issue comments |
| get_transitions | Retrieve valid workflow transitions |

---

## 💬 Example Prompts

```text
What projects do I have access to?

Show all open issues in project MP

Create a task in project MP:
"Fix navbar bug"
priority High
due 2026-05-01
assign to me

Assign MP-3 to me and move it to In Progress

Add comment to MP-5:
"Blocked by API rate limits, investigating"

Move MP-7 to Done

Show all bugs assigned to me

Set priority of MP-2 to Highest and due date to next Friday

Create a story:
"User can reset password via email"
```

---

## 📈 Project Metrics

- ✅ 10+ Jira Automation Tools
- ✅ OAuth 2.0 Integration
- ✅ MCP-Based Tool Architecture
- ✅ Production Cloud Deployment
- ✅ PostgreSQL Persistence
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

### Installation

```bash
git clone https://github.com/YOUR_USERNAME/jira-ai-agent.git

cd jira-ai-agent

python -m venv .venv

source .venv/bin/activate
# Windows
.venv\Scripts\activate

pip install -r requirements.txt
```

### Configure Environment

```bash
cp .env.example .env
```

Fill in:

```env
ATLASSIAN_CLIENT_ID=your_client_id
ATLASSIAN_CLIENT_SECRET=your_client_secret
ATLASSIAN_REDIRECT_URI=http://localhost:8000/auth/callback

GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash

JWT_SECRET=your_secret
ENCRYPTION_KEY=your_fernet_key

DATABASE_URL=postgresql://...

APP_ENV=development

FRONTEND_URL=http://localhost:8000
```

### Run

```bash
uvicorn app.main:app --reload --port 8000
```

Open:

```text
http://localhost:8000
```

---

## 🌐 Production Deployment

### Render

Build Command

```bash
pip install -r requirements.txt
```

Start Command

```bash
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Production Environment Variables

```env
APP_ENV=production

DATABASE_URL=<Neon PostgreSQL URL>

JWT_SECRET=<secret>

ENCRYPTION_KEY=<fernet_key>

ATLASSIAN_CLIENT_ID=<client_id>

ATLASSIAN_CLIENT_SECRET=<client_secret>

ATLASSIAN_REDIRECT_URI=https://zira-automation-agent.onrender.com/auth/callback

GEMINI_API_KEY=<api_key>

GEMINI_MODEL=gemini-2.5-flash

FRONTEND_URL=https://zira-automation-agent.onrender.com
```

---

## 🗺️ Roadmap

- [ ] Multi-Agent Workflows
- [ ] Confluence Integration
- [ ] Slack Integration
- [ ] Streaming Responses
- [ ] Audit Logging Dashboard
- [ ] Multi-Tenant Jira Support
- [ ] Analytics Dashboard
- [ ] Role-Based Access Control

---

## 🏆 Engineering Highlights

### Agentic AI Systems

- Multi-step tool-calling workflows
- Function calling with Gemini
- Context-aware orchestration
- Identity-aware prompt injection

### Authentication & Security

- OAuth 2.0 Authorization Code Flow
- CSRF Protection
- Encrypted OAuth token storage
- User-level credential isolation

### Backend Engineering

- FastAPI Async Architecture
- SQLAlchemy Async ORM
- Dependency Injection
- Modular Service Design

### Production Infrastructure

- Render Deployment
- Neon PostgreSQL
- Alembic Migrations
- Environment-driven Configuration

### AI Engineering

- Tool-Augmented LLM Workflows
- MCP Integration
- Prompt Engineering
- Function Calling Systems
- Real-world Agent Design

---

## 📁 Project Structure

```text
jira-ai-agent/
│
├── app/
│   ├── core/
│   │   ├── config.py
│   │   ├── crypto.py
│   │   └── database.py
│   │
│   ├── models/
│   │   └── user.py
│   │
│   ├── routers/
│   │   ├── auth.py
│   │   └── agent.py
│   │
│   ├── services/
│   │   ├── oauth_service.py
│   │   └── agent_service.py
│   │
│   └── main.py
│
├── frontend/
│   └── index.html
│
├── mcp_server/
│
├── requirements.txt
│
└── README.md
```

---

## 👨‍💻 Author

### Anmol Rajpoot

**B.Tech, Computer Science & Engineering**

Indian Institute of Information Technology (IIIT) Bhopal

### Areas of Interest

- Agentic AI
- Generative AI
- LLM Applications
- NLP Systems
- Retrieval-Augmented Generation
- Full-Stack AI Products

### Connect

GitHub: https://github.com/AnmolRajpoot25

LinkedIn: https://www.linkedin.com/in/anmol-rajpoot/

---

## 📄 License

MIT License

Copyright (c) 2026 Anmol Rajpoot

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files to deal in the Software without restriction.

---

⭐ If you found this project useful, consider giving it a star on GitHub.