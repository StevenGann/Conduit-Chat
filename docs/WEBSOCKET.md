# WebSocket Protocol

Conduit Chat uses WebSockets for real-time delivery of new messages to connected clients.

## Endpoint

```
WS /ws?token=<jwt_or_api_token>
```

- **URL:** `ws://host:port/ws` (or `wss://` over TLS)
- **Query parameter:** `token` — JWT (human) or API token (bot). Required.
- **Auth:** Invalid tokens cause immediate close with code `4001`.

## Connection Lifecycle

1. **Connect** with a valid token.
2. **Receive** message events as JSON.
3. **Disconnect** when the client closes or the server terminates the connection.

The server does not require clients to send messages; it only pushes events. Clients may send arbitrary text (e.g. ping) to keep the connection alive; the server ignores the content.

## Message Format

All server→client messages are JSON objects with a `type` field.

### New Message

When a new message is sent to a DM or room the user participates in:

```json
{
  "type": "message",
  "conversation_type": "dm",
  "conversation_id": 1,
  "message": {
    "id": 42,
    "sender_id": 2,
    "sender_username": "bob",
    "content": "Hello!",
    "created_at": "2025-03-15T01:00:00"
  }
}
```

| Field | Values | Description |
|-------|--------|-------------|
| `conversation_type` | `"dm"` \| `"room"` | Type of conversation |
| `conversation_id` | int | DM id or room id |
| `message` | object | Same shape as REST API message response |

## Client Behavior

- **Subscribe:** The server automatically delivers messages for all DMs and rooms the user is in. No subscribe/unsubscribe calls.
- **Filtering:** Filter by `conversation_type` and `conversation_id` to update only the active conversation.
- **Reconnect:** If the connection drops, reconnect with the same token. Fetch missed messages via `GET .../messages?since=<last_id>` if needed.
- **Heartbeat:** Optional; sending any text frame can help keep the connection alive through proxies.

## Example (JavaScript)

```javascript
const token = "your-jwt-or-api-token";
const ws = new WebSocket(`ws://localhost:8080/ws?token=${encodeURIComponent(token)}`);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === "message") {
    console.log(`New message in ${data.conversation_type} ${data.conversation_id}:`, data.message);
  }
};

ws.onclose = (e) => {
  if (e.code === 4001) console.error("Invalid token");
  // Consider reconnecting with backoff
};
```

## Example (Python)

```python
import asyncio
import json
import os
import websockets

async def listen(token: str, base_url: str = "ws://localhost:8080"):
    uri = f"{base_url}/ws?token={token}"
    async with websockets.connect(uri) as ws:
        async for msg in ws:
            data = json.loads(msg)
            if data.get("type") == "message":
                print(f"New message: {data['message']}")

asyncio.run(listen(os.environ["CONDUIT_TOKEN"]))
```
