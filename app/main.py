import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import get_settings
from app.core.database import init_db
from app.routers import auth, agent

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

settings = get_settings()

app = FastAPI(
    title="Jira AI Agent",
    description="OAuth-authenticated Jira agent powered by Gemini + FastAPI",
    version="0.1.0",
)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie="jira_agent_session",
    max_age=3600,
    https_only=False,
    same_site="lax",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://127.0.0.1:8000/"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(agent.router)

@app.on_event("startup")
async def on_startup():
    await init_db()

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/")
async def serve_frontend():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
