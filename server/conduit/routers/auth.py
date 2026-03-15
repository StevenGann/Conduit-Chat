import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, status

from ..auth import create_access_token, hash_password, verify_password
from ..config import get_settings
from ..database import get_db
from ..deps import get_current_human_user
from ..schemas import ChangePasswordRequest, LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    conn: aiosqlite.Connection = Depends(get_db),
):
    cursor = await conn.execute(
        "SELECT id, username, password_hash, uses_default_password FROM users "
        "WHERE username = ? AND is_bot = 0",
        (body.username,),
    )
    row = await cursor.fetchone()
    await cursor.close()

    if not row or not row["password_hash"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not verify_password(body.password, row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token = create_access_token(body.username, is_bot=False)
    return LoginResponse(
        access_token=token,
        requires_password_change=bool(row["uses_default_password"]),
    )


@router.put("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    user: dict = Depends(get_current_human_user),
    conn: aiosqlite.Connection = Depends(get_db),
):
    cursor = await conn.execute(
        "SELECT password_hash FROM users WHERE id = ?",
        (user["id"],),
    )
    row = await cursor.fetchone()
    await cursor.close()

    if not row or not verify_password(body.current_password, row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    new_hash = hash_password(body.new_password)
    await conn.execute(
        "UPDATE users SET password_hash = ?, uses_default_password = 0 WHERE id = ?",
        (new_hash, user["id"]),
    )
    await conn.commit()
    return {"ok": True}
