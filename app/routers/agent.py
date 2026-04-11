from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.user import User
from app.services import agent_service

router = APIRouter(prefix="/agent", tags=["agent"])


class ChatRequest(BaseModel):
    prompt: str


class ChatResponse(BaseModel):
    response: str
    tool_calls: list[dict]
    iterations: int


def _require_user_id(request: Request) -> int:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    return user_id


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(_require_user_id),
):
    if not body.prompt.strip():
        raise HTTPException(status_code=422, detail="Prompt cannot be empty.")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    output = await agent_service.run_agent(db, user, body.prompt)
    return ChatResponse(**output)