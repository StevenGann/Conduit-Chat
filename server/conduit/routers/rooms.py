import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, status

from ..database import get_db
from ..deps import get_current_user
from ..schemas import CreateRoomRequest, SendMessageRequest, UpdateMembersRequest
from ..websocket import manager as ws_manager

router = APIRouter(prefix="/rooms", tags=["rooms"])


async def _get_room_member(conn: aiosqlite.Connection, room_id: int, user_id: int) -> dict | None:
    cursor = await conn.execute(
        "SELECT role FROM room_members WHERE room_id = ? AND user_id = ?",
        (room_id, user_id),
    )
    row = await cursor.fetchone()
    await cursor.close()
    return dict(row) if row else None


@router.get("")
async def list_rooms(
    user: dict = Depends(get_current_user),
    conn: aiosqlite.Connection = Depends(get_db),
):
    cursor = await conn.execute(
        """
        SELECT r.id, r.name, r.created_at, rm.role
        FROM room_members rm
        JOIN rooms r ON r.id = rm.room_id
        WHERE rm.user_id = ?
        ORDER BY r.name
        """,
        (user["id"],),
    )
    rows = await cursor.fetchall()
    await cursor.close()
    return [{"id": row["id"], "name": row["name"], "role": row["role"]} for row in rows]


@router.post("")
async def create_room(
    body: CreateRoomRequest,
    user: dict = Depends(get_current_user),
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
            (room_id, user["id"]),
        )
        await conn.commit()
        return {"id": room_id, "name": name}
    except aiosqlite.IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Room name exists")


@router.get("/{room_id}")
async def get_room(
    room_id: int,
    user: dict = Depends(get_current_user),
    conn: aiosqlite.Connection = Depends(get_db),
):
    member = await _get_room_member(conn, room_id, user["id"])
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    cursor = await conn.execute(
        "SELECT id, name, created_at FROM rooms WHERE id = ?",
        (room_id,),
    )
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


@router.put("/{room_id}/members")
async def update_room_members(
    room_id: int,
    body: UpdateMembersRequest,
    user: dict = Depends(get_current_user),
    conn: aiosqlite.Connection = Depends(get_db),
):
    add = body.add or []
    remove = body.remove or []
    member = await _get_room_member(conn, room_id, user["id"])
    if not member or member["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")

    if add:
        for username in add:
            cursor = await conn.execute("SELECT id FROM users WHERE username = ?", (username,))
            u = await cursor.fetchone()
            await cursor.close()
            if u:
                try:
                    await conn.execute(
                        "INSERT OR IGNORE INTO room_members (room_id, user_id, role) VALUES (?, ?, 'member')",
                        (room_id, u["id"]),
                    )
                except aiosqlite.IntegrityError:
                    pass
        await conn.commit()

    if remove:
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


@router.get("/{room_id}/messages")
async def get_room_messages(
    room_id: int,
    since: int | None = None,
    limit: int = 50,
    user: dict = Depends(get_current_user),
    conn: aiosqlite.Connection = Depends(get_db),
):
    member = await _get_room_member(conn, room_id, user["id"])
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    if since:
        cursor = await conn.execute(
            """
            SELECT m.id, m.sender_id, m.content, m.created_at, u.username as sender_username
            FROM messages m
            JOIN users u ON u.id = m.sender_id
            WHERE m.conversation_type = 'room' AND m.conversation_id = ? AND m.id > ?
            ORDER BY m.id ASC
            LIMIT ?
            """,
            (room_id, since, limit),
        )
    else:
        cursor = await conn.execute(
            """
            SELECT m.id, m.sender_id, m.content, m.created_at, u.username as sender_username
            FROM messages m
            JOIN users u ON u.id = m.sender_id
            WHERE m.conversation_type = 'room' AND m.conversation_id = ?
            ORDER BY m.id DESC
            LIMIT ?
            """,
            (room_id, limit),
        )
    rows = await cursor.fetchall()
    await cursor.close()

    messages = [
        {
            "id": row["id"],
            "sender_id": row["sender_id"],
            "sender_username": row["sender_username"],
            "content": row["content"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]
    if not since:
        messages.reverse()
    return {"messages": messages}


@router.post("/{room_id}/messages")
async def send_room_message(
    room_id: int,
    body: SendMessageRequest,
    user: dict = Depends(get_current_user),
    conn: aiosqlite.Connection = Depends(get_db),
):
    member = await _get_room_member(conn, room_id, user["id"])
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    content = body.content
    if not content or not content.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Content required")
    if len(content) > 65536:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Content too long")

    await conn.execute(
        "INSERT INTO messages (conversation_type, conversation_id, sender_id, content) "
        "VALUES ('room', ?, ?, ?)",
        (room_id, user["id"], content.strip()),
    )
    await conn.commit()
    cursor = await conn.execute(
        "SELECT id, created_at FROM messages WHERE id = last_insert_rowid()"
    )
    row = await cursor.fetchone()
    await cursor.close()

    msg = {
        "id": row["id"],
        "sender_id": user["id"],
        "sender_username": user["username"],
        "content": content.strip(),
        "created_at": row["created_at"],
    }

    cursor = await conn.execute(
        "SELECT user_id FROM room_members WHERE room_id = ?",
        (room_id,),
    )
    members = await cursor.fetchall()
    await cursor.close()
    participant_ids = [m["user_id"] for m in members]
    await ws_manager.broadcast_to_conversation(
        participant_ids,
        {"type": "message", "conversation_type": "room", "conversation_id": room_id, "message": msg},
    )

    return msg
