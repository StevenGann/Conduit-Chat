import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, status

from ..auth import generate_api_token, hash_password
from ..config import get_settings
from ..database import get_db
from ..deps import get_current_user
from ..schemas import CreateRoomRequest, CreateUserRequest, CreateUserResponse, UpdateMembersRequest, UpdateRoomRequest, UserResponse

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


@router.get("/rooms/{room_id}")
async def get_admin_room(
    room_id: int,
    _admin: dict = Depends(require_admin),
    conn: aiosqlite.Connection = Depends(get_db),
):
    cursor = await conn.execute("SELECT id, name, created_at FROM rooms WHERE id = ?", (room_id,))
    room = await cursor.fetchone()
    await cursor.close()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    cursor = await conn.execute(
        """
        SELECT u.id, u.username, rm.role
        FROM room_members rm
        JOIN users u ON u.id = rm.user_id
        WHERE rm.room_id = ?
        """,
        (room_id,),
    )
    members = await cursor.fetchall()
    await cursor.close()

    return {
        "id": room["id"],
        "name": room["name"],
        "created_at": room["created_at"],
        "members": [{"id": m["id"], "username": m["username"], "role": m["role"]} for m in members],
    }


@router.post("/rooms", response_model=dict)
async def create_admin_room(
    body: CreateRoomRequest,
    admin: dict = Depends(require_admin),
    conn: aiosqlite.Connection = Depends(get_db),
):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Room name required")
    try:
        await conn.execute("INSERT INTO rooms (name) VALUES (?)", (name,))
        await conn.commit()
        cursor = await conn.execute("SELECT last_insert_rowid() as id")
        row = await cursor.fetchone()
        await cursor.close()
        room_id = row["id"]
        await conn.execute(
            "INSERT INTO room_members (room_id, user_id, role) VALUES (?, ?, 'admin')",
            (room_id, admin["id"]),
        )
        await conn.commit()
        return {"id": room_id, "name": name}
    except aiosqlite.IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Room name exists")


@router.put("/rooms/{room_id}")
async def update_admin_room(
    room_id: int,
    body: UpdateRoomRequest,
    _admin: dict = Depends(require_admin),
    conn: aiosqlite.Connection = Depends(get_db),
):
    if body.name is None or not body.name.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Room name required")
    cursor = await conn.execute("SELECT id FROM rooms WHERE id = ?", (room_id,))
    if not await cursor.fetchone():
        await cursor.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    await cursor.close()
    try:
        await conn.execute("UPDATE rooms SET name = ? WHERE id = ?", (body.name.strip(), room_id))
        await conn.commit()
        return {"ok": True}
    except aiosqlite.IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Room name exists")


@router.put("/rooms/{room_id}/members")
async def update_admin_room_members(
    room_id: int,
    body: UpdateMembersRequest,
    _admin: dict = Depends(require_admin),
    conn: aiosqlite.Connection = Depends(get_db),
):
    add = body.add or []
    remove = body.remove or []

    cursor = await conn.execute("SELECT id FROM rooms WHERE id = ?", (room_id,))
    if not await cursor.fetchone():
        await cursor.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    await cursor.close()

    for username in add:
        cursor = await conn.execute("SELECT id FROM users WHERE username = ?", (username,))
        u = await cursor.fetchone()
        await cursor.close()
        if u:
            await conn.execute(
                "INSERT OR IGNORE INTO room_members (room_id, user_id, role) VALUES (?, ?, 'member')",
                (room_id, u["id"]),
            )
    for username in remove:
        cursor = await conn.execute("SELECT id FROM users WHERE username = ?", (username,))
        u = await cursor.fetchone()
        await cursor.close()
        if u:
            await conn.execute(
                "DELETE FROM room_members WHERE room_id = ? AND user_id = ? AND role != 'admin'",
                (room_id, u["id"]),
            )
    await conn.commit()
    return {"ok": True}


@router.delete("/rooms/{room_id}")
async def delete_admin_room(
    room_id: int,
    _admin: dict = Depends(require_admin),
    conn: aiosqlite.Connection = Depends(get_db),
):
    await conn.execute("DELETE FROM room_members WHERE room_id = ?", (room_id,))
    await conn.execute("DELETE FROM messages WHERE conversation_type = 'room' AND conversation_id = ?", (room_id,))
    await conn.execute("DELETE FROM rooms WHERE id = ?", (room_id,))
    await conn.commit()
    return {"ok": True}


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
