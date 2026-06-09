from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.models.user import User

ALGORITHM = "HS256"

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return password_context.verify(plain_password, password_hash)


def create_access_token(user: User) -> str:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "exp": expires_at,
        "typ": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def create_oauth_state(user: User) -> str:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    payload = {
        "sub": str(user.id),
        "exp": expires_at,
        "typ": "atlassian_oauth",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def verify_oauth_state(state: str) -> int:
    settings = get_settings()
    try:
        payload = jwt.decode(state, settings.jwt_secret, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=400, detail="Invalid OAuth state.") from exc
    if payload.get("typ") != "atlassian_oauth":
        raise HTTPException(status_code=400, detail="Invalid OAuth state.")
    return int(payload["sub"])


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
        )

    settings = get_settings()
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[ALGORITHM],
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        ) from exc

    if payload.get("typ") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")

    result = await db.execute(select(User).where(User.id == int(payload["sub"])))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    return user
