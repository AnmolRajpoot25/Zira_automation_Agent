from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import create_oauth_state, get_current_user, verify_oauth_state
from app.models.user import JiraConnection, User
from app.services import oauth_service

router = APIRouter(prefix="/jira", tags=["jira"])
settings = get_settings()


@router.get("/connect")
async def connect_jira(user: User = Depends(get_current_user)):
    state = create_oauth_state(user)
    return {"authorization_url": oauth_service.build_authorization_url(state)}


@router.get("/callback")
async def jira_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    user_id = verify_oauth_state(state)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")

    token_data = await oauth_service.exchange_code_for_tokens(code)
    cloud_id = await oauth_service.fetch_cloud_id(token_data["access_token"])
    await oauth_service.upsert_jira_connection(db, user, cloud_id, token_data)
    return RedirectResponse(f"{settings.frontend_url}/?jira=connected")


@router.delete("/disconnect")
async def disconnect_jira(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(delete(JiraConnection).where(JiraConnection.user_id == user.id))
    await db.commit()
    return {"message": "Jira disconnected."}
