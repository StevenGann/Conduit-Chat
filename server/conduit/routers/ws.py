from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from ..auth import decode_token
from ..database import get_db_conn
from ..websocket import manager as ws_manager

router = APIRouter(tags=["ws"])


async def get_user_from_token(token: str) -> dict | None:
    payload = decode_token(token)
    conn = await get_db_conn()
    try:
        if payload:
            username = payload.get("sub")
            if username:
                cursor = await conn.execute(
                    "SELECT id, username FROM users WHERE username = ? AND is_bot = 0",
                    (username,),
                )
                row = await cursor.fetchone()
                await cursor.close()
                if row:
                    return {"id": row["id"], "username": row["username"]}
            return None

        cursor = await conn.execute(
            "SELECT id, username FROM users WHERE api_token = ? AND is_bot = 1",
            (token,),
        )
        row = await cursor.fetchone()
        await cursor.close()
        if row:
            return {"id": row["id"], "username": row["username"]}
        return None
    finally:
        await conn.close()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT or API token"),
):
    user = await get_user_from_token(token)
    if not user:
        await websocket.close(code=4001)
        return

    await ws_manager.connect(websocket, user["id"])
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(websocket, user["id"])
