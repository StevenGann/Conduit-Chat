import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, status

from ..auth import hash_password
from ..config import get_settings
from ..database import get_db
from ..schemas import SetupRequest

router = APIRouter(prefix="/api", tags=["setup"])


@router.post("/setup")
async def setup(
    body: SetupRequest,
    conn: aiosqlite.Connection = Depends(get_db),
):
    """Create the first admin user when no users exist. Unauthenticated."""
    settings = get_settings()
    if not settings.secret_key or not settings.default_password:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Server not configured: SECRET_KEY and DEFAULT_PASSWORD required",
        )

    cursor = await conn.execute("SELECT COUNT(*) as n FROM users")
    row = await cursor.fetchone()
    await cursor.close()

    if row["n"] > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Setup already completed",
        )

    password_hash = hash_password(body.password)
    await conn.execute(
        "INSERT INTO users (username, password_hash, is_bot, uses_default_password) "
        "VALUES (?, ?, 0, 0)",
        (body.username, password_hash),
    )
    await conn.commit()
    return {"ok": True, "message": "First admin user created"}
