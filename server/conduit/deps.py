import aiosqlite
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .auth import decode_token
from .config import get_settings
from .database import get_db

security = HTTPBearer(auto_error=False)


async def get_current_user(
    conn: aiosqlite.Connection = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict:
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    token = credentials.credentials

    # Try JWT first
    payload = decode_token(token)
    if payload:
        username = payload.get("sub")
        if username:
            cursor = await conn.execute(
                "SELECT id, username, is_bot FROM users WHERE username = ? AND is_bot = 0",
                (username,),
            )
            row = await cursor.fetchone()
            await cursor.close()
            if row:
                return {"id": row["id"], "username": row["username"], "is_bot": False}
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    # Try api_token for bots
    cursor = await conn.execute(
        "SELECT id, username, is_bot FROM users WHERE api_token = ? AND is_bot = 1",
        (token,),
    )
    row = await cursor.fetchone()
    await cursor.close()
    if row:
        return {"id": row["id"], "username": row["username"], "is_bot": True}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token",
    )


async def get_current_human_user(
    user: dict = Depends(get_current_user),
) -> dict:
    if user.get("is_bot"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires a human user",
        )
    return user


