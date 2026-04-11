from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.config import get_settings
from app.models.user import User
from app.services import oauth_service

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


def _get_session_user_id(request: Request) -> int | None:
    return request.session.get("user_id")


@router.get("/login")
async def login(request: Request):
    url, state = oauth_service.build_authorization_url()
    request.session["oauth_state"] = state
    return RedirectResponse(url)


@router.get("/callback")
async def callback(
    request: Request,
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    token_data = await oauth_service.exchange_code_for_tokens(code)
    identity = await oauth_service.fetch_user_identity(token_data["access_token"])
    user = await oauth_service.upsert_user(db, identity, token_data)
    request.session["user_id"] = user.id
    request.session["account_id"] = user.account_id
    return RedirectResponse(f"{settings.frontend_url}/auth/set-session?uid={user.id}")


@router.get("/set-session")
async def set_session(request: Request, uid: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    request.session["user_id"] = uid
    response = RedirectResponse(f"{settings.frontend_url}?login=success")
    return response


@router.get("/me")
async def me(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = _get_session_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return {
        "account_id": user.account_id,
        "email": user.email,
        "display_name": user.display_name,
        "jira_base_url": user.jira_base_url,
    }


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return JSONResponse({"message": "Logged out."})


@router.get("/debug-session")
async def debug_session(request: Request):
    if settings.app_env != "development":
        raise HTTPException(status_code=404)
    return {"session": dict(request.session), "cookies": dict(request.cookies)}
