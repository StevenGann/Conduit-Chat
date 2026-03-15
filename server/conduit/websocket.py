from collections import defaultdict

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        # user_id -> set of WebSocket
        self._connections: dict[int, set[WebSocket]] = defaultdict(set)

    async def connect(self, websocket: WebSocket, user_id: int) -> None:
        await websocket.accept()
        self._connections[user_id].add(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int) -> None:
        self._connections[user_id].discard(websocket)
        if not self._connections[user_id]:
            del self._connections[user_id]

    async def broadcast_to_user(self, user_id: int, message: dict) -> None:
        dead = set()
        for ws in self._connections.get(user_id, []):
            try:
                await ws.send_json(message)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self._connections[user_id].discard(ws)

    async def broadcast_to_conversation(
        self,
        participant_ids: list[int],
        message: dict,
    ) -> None:
        for uid in participant_ids:
            await self.broadcast_to_user(uid, message)


manager = ConnectionManager()
