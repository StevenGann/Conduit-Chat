import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, status

from ..database import get_db
from ..deps import get_current_user
from ..schemas import CreateDmRequest, SendMessageRequest
from ..websocket import manager as ws_manager

router = APIRouter(prefix="/dms", tags=["dms"])


@router.get("")
async def list_dms(
    user: dict = Depends(get_current_user),
    conn: aiosqlite.Connection = Depends(get_db),
):
    cursor = await conn.execute(
        """
        SELECT d.id, d.user1_id, d.user2_id, d.created_at,
               u.username as other_username
        FROM dm_conversations d
        JOIN users u ON u.id = CASE WHEN d.user1_id = ? THEN d.user2_id ELSE d.user1_id END
        WHERE d.user1_id = ? OR d.user2_id = ?
        ORDER BY d.created_at DESC
        """,
        (user["id"], user["id"], user["id"]),
    )
    rows = await cursor.fetchall()
    await cursor.close()
    return [
        {
            "id": row["id"],
            "other_username": row["other_username"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


@router.post("")
async def create_or_find_dm(
    body: CreateDmRequest,
    user: dict = Depends(get_current_user),
    conn: aiosqlite.Connection = Depends(get_db),
):
    target_username = body.target_username
    if target_username == user["username"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create DM with yourself",
        )

    cursor = await conn.execute(
        "SELECT id FROM users WHERE username = ?",
        (target_username,),
    )
    target = await cursor.fetchone()
    await cursor.close()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    uid1, uid2 = min(user["id"], target["id"]), max(user["id"], target["id"])
    cursor = await conn.execute(
        "SELECT id FROM dm_conversations WHERE user1_id = ? AND user2_id = ?",
        (uid1, uid2),
    )
    existing = await cursor.fetchone()
    await cursor.close()

    if existing:
        return {"id": existing["id"], "other_username": target_username}

    await conn.execute(
        "INSERT INTO dm_conversations (user1_id, user2_id) VALUES (?, ?)",
        (uid1, uid2),
    )
    await conn.commit()
    cursor = await conn.execute("SELECT last_insert_rowid() as id, datetime('now') as created_at")
    row = await cursor.fetchone()
    await cursor.close()
    return {"id": row["id"], "other_username": target_username}


@router.get("/{dm_id}/messages")
async def get_dm_messages(
    dm_id: int,
    since: int | None = None,
    limit: int = 50,
    user: dict = Depends(get_current_user),
    conn: aiosqlite.Connection = Depends(get_db),
):
    cursor = await conn.execute(
        "SELECT user1_id, user2_id FROM dm_conversations WHERE id = ?",
        (dm_id,),
    )
    dm = await cursor.fetchone()
    await cursor.close()
    if not dm or (user["id"] != dm["user1_id"] and user["id"] != dm["user2_id"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DM not found")

    if since:
        cursor = await conn.execute(
            """
            SELECT m.id, m.sender_id, m.content, m.created_at, u.username as sender_username
            FROM messages m
            JOIN users u ON u.id = m.sender_id
            WHERE m.conversation_type = 'dm' AND m.conversation_id = ? AND m.id > ?
            ORDER BY m.id ASC
            LIMIT ?
            """,
            (dm_id, since, limit),
        )
    else:
        cursor = await conn.execute(
            """
            SELECT m.id, m.sender_id, m.content, m.created_at, u.username as sender_username
            FROM messages m
            JOIN users u ON u.id = m.sender_id
            WHERE m.conversation_type = 'dm' AND m.conversation_id = ?
            ORDER BY m.id DESC
            LIMIT ?
            """,
            (dm_id, limit),
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


@router.post("/{dm_id}/messages")
async def send_dm_message(
    dm_id: int,
    body: SendMessageRequest,
    user: dict = Depends(get_current_user),
    conn: aiosqlite.Connection = Depends(get_db),
):
    content = body.content
    if not content or not content.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Content required")
    if len(content) > 65536:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Content too long")

    cursor = await conn.execute(
        "SELECT user1_id, user2_id FROM dm_conversations WHERE id = ?",
        (dm_id,),
    )
    dm = await cursor.fetchone()
    await cursor.close()
    if not dm or (user["id"] != dm["user1_id"] and user["id"] != dm["user2_id"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DM not found")

    await conn.execute(
        "INSERT INTO messages (conversation_type, conversation_id, sender_id, content) "
        "VALUES ('dm', ?, ?, ?)",
        (dm_id, user["id"], content.strip()),
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
    participant_ids = [dm["user1_id"], dm["user2_id"]]
    await ws_manager.broadcast_to_conversation(
        participant_ids,
        {"type": "message", "conversation_type": "dm", "conversation_id": dm_id, "message": msg},
    )

    return msg
