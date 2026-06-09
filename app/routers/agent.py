from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services import agent_service

router = APIRouter(prefix="/agent", tags=["agent"])


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)

    @field_validator("prompt")
    @classmethod
    def prompt_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Prompt cannot be empty.")
        return value


class ChatResponse(BaseModel):
    response: str
    tool_calls: list[dict]
    iterations: int


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.encrypted_gemini_key is None:
        raise HTTPException(status_code=400, detail="Add your Gemini API key in settings first.")

    output = await agent_service.run_agent(db, user, body.prompt)
    return ChatResponse(**output)
