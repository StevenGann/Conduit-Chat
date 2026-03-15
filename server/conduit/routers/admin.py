import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, status

from ..auth import generate_api_token, hash_password
from ..config import get_settings
from ..database import get_db
from ..deps import get_current_user
from ..schemas import CreateUserRequest, CreateUserResponse, UserResponse

router = APIRouter(prefix="/admin", tags=["admin"])


async def is_admin(conn: aiosqlite.Connection, user_id: int, username: str) -> bool:
    settings = get_settings()
    if settings.admin_username and username == settings.admin_username:
        return True
    cursor = await conn.execute(
        "SELECT id FROM users ORDER BY id ASC LIMIT 1"
    )
    row = await cursor.fetchone()
    await cursor.close()
    return row is not None and row["id"] == user_id


async def require_admin(
    user: dict = Depends(get_current_user),
    conn: aiosqlite.Connection = Depends(get_db),
) -> dict:
    if not await is_admin(conn, user["id"], user["username"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
    return user


@router.get("/config")
async def get_config(_admin: dict = Depends(require_admin)):
    settings = get_settings()
    return {
        "database_path": settings.database_path,
        "port": settings.port,
        "serve_web_app": settings.serve_web_app,
        "origin": settings.origin,
    }


@router.get("/connections")
async def get_connections(_admin: dict = Depends(require_admin)):
    from ..websocket import manager as ws_manager
    return {
        "websocket": sum(len(s) for s in ws_manager._connections.values()),
    }


@router.get("/rooms")
async def list_all_rooms(
    _admin: dict = Depends(require_admin),
    conn: aiosqlite.Connection = Depends(get_db),
):
    cursor = await conn.execute(
        """
        SELECT r.id, r.name, r.created_at,
               (SELECT COUNT(*) FROM room_members WHERE room_id = r.id) as member_count
        FROM rooms r
        ORDER BY r.name
        """
    )
    rows = await cursor.fetchall()
    await cursor.close()
    return [
        {"id": row["id"], "name": row["name"], "member_count": row["member_count"]}
        for row in rows
    ]


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    _admin: dict = Depends(require_admin),
    conn: aiosqlite.Connection = Depends(get_db),
):
    cursor = await conn.execute(
        "SELECT id, username, is_bot, uses_default_password FROM users"
    )
    rows = await cursor.fetchall()
    await cursor.close()
    return [
        UserResponse(
            id=row["id"],
            username=row["username"],
            is_bot=bool(row["is_bot"]),
            uses_default_password=bool(row["uses_default_password"]) if not row["is_bot"] else None,
        )
        for row in rows
    ]


@router.post("/users", response_model=CreateUserResponse)
async def create_user(
    body: CreateUserRequest,
    _admin: dict = Depends(require_admin),
    conn: aiosqlite.Connection = Depends(get_db),
):
    settings = get_settings()
    if not settings.default_password and not body.is_bot:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DEFAULT_PASSWORD not configured",
        )

    try:
        if body.is_bot:
            api_token = generate_api_token()
            await conn.execute(
                "INSERT INTO users (username, is_bot, api_token, uses_default_password) "
                "VALUES (?, 1, ?, 0)",
                (body.username, api_token),
            )
        else:
            password_hash = hash_password(settings.default_password)
            await conn.execute(
                "INSERT INTO users (username, password_hash, is_bot, uses_default_password) "
                "VALUES (?, ?, 0, 1)",
                (body.username, password_hash),
            )
            api_token = None
        await conn.commit()
    except aiosqlite.IntegrityError as e:
        if "UNIQUE" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already exists",
            )
        raise

    cursor = await conn.execute(
        "SELECT id, username, is_bot FROM users WHERE username = ?",
        (body.username,),
    )
    row = await cursor.fetchone()
    await cursor.close()

    return CreateUserResponse(
        id=row["id"],
        username=row["username"],
        is_bot=row["is_bot"],
        api_token=api_token,
    )
