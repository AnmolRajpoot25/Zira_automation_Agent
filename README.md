# Jira AI Agent SaaS

Production-ready multi-user Jira automation SaaS built with FastAPI, PostgreSQL, SQLAlchemy async, Alembic, Atlassian OAuth 2.0 3LO, JWT authentication, encrypted credentials, and Google Gemini.

## Features

- Register, login, logout, and current-user endpoints with JWT bearer auth
- Password hashing with bcrypt
- PostgreSQL persistence with SQLAlchemy async models
- Alembic migrations for schema management
- Atlassian OAuth 2.0 3LO connect, callback, and disconnect flow
- Stores Jira `cloud_id`, access token, refresh token, and expiry per user
- Refresh token rotation support
- Per-user encrypted Gemini API key
- Fernet encryption for all credentials at rest
- Auth dependency, CORS, in-memory rate limiting, and Pydantic input validation
- Static frontend pages for Login, Register, Dashboard, and Settings
- Dockerfile, Procfile, and Railway configuration

## Required Environment Variables

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/jira_agent
JWT_SECRET=replace-with-a-long-random-secret
ENCRYPTION_KEY=replace-with-fernet-key
ATLASSIAN_CLIENT_ID=your-atlassian-client-id
ATLASSIAN_CLIENT_SECRET=your-atlassian-client-secret
ATLASSIAN_REDIRECT_URI=http://localhost:8000/jira/callback
FRONTEND_URL=http://localhost:8000
APP_ENV=production
CORS_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
GEMINI_MODEL=gemini-2.5-flash
```

Generate an encryption key:

```bash
python -m app.core.crypto
```

Generate a JWT secret:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

## Database Schema

`users`

- `id`
- `name`
- `email`
- `password_hash`
- `encrypted_gemini_key`
- `created_at`

`jira_connections`

- `id`
- `user_id`
- `cloud_id`
- `encrypted_access_token`
- `encrypted_refresh_token`
- `expires_at`

## Local Development

1. Create a PostgreSQL database.

2. Install dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and fill in values.

4. Run migrations:

```bash
alembic upgrade head
```

5. Start the app:

```bash
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000`.

## Atlassian OAuth Setup

Create an OAuth 2.0 app in the Atlassian Developer Console and enable Jira platform scopes:

- `read:jira-work`
- `write:jira-work`
- `read:jira-user`
- `offline_access`

Set the callback URL to:

```text
http://localhost:8000/jira/callback
```

For production, use your deployed URL:

```text
https://YOUR-APP.railway.app/jira/callback
```

## API Overview

Auth:

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me`
- `POST /auth/gemini-key`

Jira OAuth:

- `GET /jira/connect`
- `GET /jira/callback`
- `DELETE /jira/disconnect`

Agent:

- `POST /agent/chat`

All authenticated endpoints require:

```text
Authorization: Bearer <jwt>
```

## Railway Deployment

1. Push the repository to GitHub.
2. Create a new Railway project from the GitHub repository.
3. Add a Railway PostgreSQL database.
4. Set `DATABASE_URL` to the Railway Postgres connection string.
5. Set all required environment variables.
6. Set `ATLASSIAN_REDIRECT_URI` to `https://YOUR-APP.railway.app/jira/callback`.
7. Deploy.

The `Procfile` and Docker image run:

```bash
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Production Notes

- Do not reuse `ENCRYPTION_KEY`; rotating it requires re-encrypting stored credentials.
- Keep `JWT_SECRET` long and private.
- Use HTTPS in production.
- Configure `CORS_ORIGINS` to trusted origins only.
- Railway and many hosted Postgres providers expose `postgres://` URLs; the app automatically converts them to SQLAlchemy async URLs.
