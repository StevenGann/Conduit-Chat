# Integration Guide

Examples for integrating with Conduit Chat as a developer or AI agent.

## Prerequisites

- Server running at `http://localhost:8080` (or your base URL)
- A human user (JWT) or bot user (API token) for authentication

---

## Bootstrap and First Login

**Auto-bootstrap:** Set `ADMIN_USERNAME` and `ADMIN_PASSWORD` in the environment; the server creates the first admin on startup when no users exist.

**Manual bootstrap:**

```bash
# 1. Create first admin user (once, when server has no users)
curl -X POST http://localhost:8080/api/setup \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"SecurePassword123"}'

# 2. Login to get JWT
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"SecurePassword123"}'
# Response: {"access_token":"eyJ...","token_type":"bearer","requires_password_change":false}
```

---

## Python Client Example

```python
import requests

BASE = "http://localhost:8080"

def login(username: str, password: str) -> str:
    r = requests.post(f"{BASE}/api/auth/login", json={"username": username, "password": password})
    r.raise_for_status()
    return r.json()["access_token"]

def send_dm(token: str, target: str, content: str) -> dict:
    # Create or find DM
    r = requests.post(
        f"{BASE}/api/dms",
        headers={"Authorization": f"Bearer {token}"},
        json={"target_username": target},
    )
    r.raise_for_status()
    dm_id = r.json()["id"]
    # Send message
    r = requests.post(
        f"{BASE}/api/dms/{dm_id}/messages",
        headers={"Authorization": f"Bearer {token}"},
        json={"content": content},
    )
    r.raise_for_status()
    return r.json()

# Usage
token = login("admin", "SecurePassword123")
msg = send_dm(token, "bob", "Hello from Python!")
print(msg)
```

---

## AI Agent / Bot Integration

### 1. Admin Creates Bot User

```bash
# Admin (with JWT) creates a bot
curl -X POST http://localhost:8080/api/admin/users \
  -H "Authorization: Bearer <admin_jwt>" \
  -H "Content-Type: application/json" \
  -d '{"username":"assistant-bot","is_bot":true}'
# Response includes "api_token" — store it; cannot be retrieved again
```

### 2. Bot Uses API Token

```python
import os
import requests

BASE = os.environ.get("CONDUIT_BASE", "http://localhost:8080")
TOKEN = os.environ["CONDUIT_API_TOKEN"]
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

def list_conversations():
    dms = requests.get(f"{BASE}/api/dms", headers=HEADERS).json()
    rooms = requests.get(f"{BASE}/api/rooms", headers=HEADERS).json()
    return {"dms": dms, "rooms": rooms}

def send_to_user(username: str, content: str):
    r = requests.post(f"{BASE}/api/dms", headers=HEADERS, json={"target_username": username})
    r.raise_for_status()
    dm_id = r.json()["id"]
    r = requests.post(f"{BASE}/api/dms/{dm_id}/messages", headers=HEADERS, json={"content": content})
    r.raise_for_status()
    return r.json()

def send_to_room(room_name: str, content: str):
    rooms = requests.get(f"{BASE}/api/rooms", headers=HEADERS).json()
    room = next((r for r in rooms if r["name"] == room_name), None)
    if not room:
        raise ValueError(f"Room '{room_name}' not found or not a member")
    r = requests.post(
        f"{BASE}/api/rooms/{room['id']}/messages",
        headers=HEADERS,
        json={"content": content},
    )
    r.raise_for_status()
    return r.json()
```

### 3. Bot Listens via WebSocket

```python
import asyncio
import json
import os
import websockets

async def listen_and_respond(token: str, handler):
    uri = f"ws://localhost:8080/ws?token={token}"
    async with websockets.connect(uri) as ws:
        async for msg in ws:
            data = json.loads(msg)
            if data.get("type") == "message":
                await handler(data)

async def my_handler(data):
    msg = data["message"]
    print(f"Received: {msg['content']} from {msg['sender_username']}")
    # Optionally: call your LLM, then send response via REST

asyncio.run(listen_and_respond(os.environ["CONDUIT_API_TOKEN"], my_handler))
```

---

## Polling for New Messages

If WebSocket is not suitable, poll using the `since` parameter:

```python
def poll_messages(token: str, conv_type: str, conv_id: int, since: int = 0):
    base = f"{BASE}/api/dms/{conv_id}/messages" if conv_type == "dm" else f"{BASE}/api/rooms/{conv_id}/messages"
    r = requests.get(base, headers=HEADERS, params={"since": since} if since else {})
    r.raise_for_status()
    return r.json()["messages"]

# Poll every 5 seconds
last_id = 0
while True:
    msgs = poll_messages(token, "dm", 1, since=last_id)
    for m in msgs:
        print(m)
        last_id = max(last_id, m["id"])
    time.sleep(5)
```

---

## cURL Cheat Sheet

```bash
# Auth
export TOKEN=$(curl -s -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" -d '{"username":"admin","password":"x"}' | jq -r .access_token)

# DMs
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8080/api/dms | jq
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"target_username":"bob"}' http://localhost:8080/api/dms | jq
curl -s -H "Authorization: Bearer $TOKEN" "http://localhost:8080/api/dms/1/messages" | jq
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"content":"Hi"}' http://localhost:8080/api/dms/1/messages | jq

# Rooms
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8080/api/rooms | jq
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"general"}' http://localhost:8080/api/rooms | jq
```
