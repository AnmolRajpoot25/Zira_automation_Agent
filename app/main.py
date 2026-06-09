import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import get_settings
from app.core.rate_limit import RateLimitMiddleware
from app.routers import agent, auth, jira

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

settings = get_settings()

app = FastAPI(
    title="Jira AI Agent",
    description="Multi-user Jira agent powered by Gemini + FastAPI",
    version="1.0.0",
)

app.add_middleware(
    RateLimitMiddleware,
    requests_per_window=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_window_seconds,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(jira.router)
app.include_router(agent.router)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/")
async def serve_frontend():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
