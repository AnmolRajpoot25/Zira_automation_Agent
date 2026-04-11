"""
Patch main.py to also serve the frontend from /frontend/index.html.
Add this to app/main.py after including routers.
"""
# Add to app/main.py imports:
#   from fastapi.staticfiles import StaticFiles
#   from fastapi.responses import FileResponse
#   import os

# Then add after app.include_router(agent.router):

# FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
# app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

# @app.get("/")
# async def serve_frontend():
#     return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
