# Conduit Chat API Reference

Base path: `/api` for all endpoints except `/health`, `/ws`, and `/api/setup`.

All requests and responses use `Content-Type: application/json` unless noted.

## Error Responses

Errors return JSON:

```json
{"detail": "Human-readable error message"}
```

| Status | Meaning |
|--------|---------|
| 400 | Bad Request — invalid input |
| 401 | Unauthorized — missing or invalid token |
| 403 | Forbidden — insufficient permissions |
| 404 | Not Found — resource does not exist or access denied |
| 409 | Conflict — e.g. duplicate username or room name |
| 503 | Service Unavailable — server misconfigured |

---

## Unauthenticated Endpoints

### Health Check

```
GET /health
```

**Response:** `200 OK`
```json
{"status": "ok"}
```

---

### Bootstrap Setup

```
POST /api/setup
```

Creates the first admin user when no users exist. **Unauthenticated.** Fails if any user already exists.

**Request body:**
```json
{
  "username": "admin",
  "password": "your-secure-password"
}
```

**Response:** `200 OK`
```json
{
  "ok": true,
  "message": "First admin user created"
}
```

**Errors:**
- `403` — Setup already completed (users exist)
- `503` — `SECRET_KEY` or `DEFAULT_PASSWORD` not configured

---

## Authentication

### Login (Human Users Only)

```
POST /api/auth/login
```

**Request body:**
```json
{
  "username": "alice",
  "password": "password123"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "requires_password_change": false
}
```

- `requires_password_change: true` — User is still on default password; should be prompted to change (non-blocking).

**Errors:** `401` — Invalid username or password

---

### Change Password

```
PUT /api/auth/change-password
```

**Auth:** Bearer JWT (human users only)

**Request body:**
```json
{
  "current_password": "old-password",
  "new_password": "new-password"
}
```

**Response:** `200 OK`
```json
{"ok": true}
```

**Errors:** `400` — Current password incorrect

---

## Direct Messages (DMs)

All DM endpoints require authentication (JWT or API token).

### List DMs

```
GET /api/dms
```

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "other_username": "bob",
    "created_at": "2025-03-15T01:00:00"
  }
]
```

---

### Create or Find DM

```
POST /api/dms
```

**Request body:**
```json
{"target_username": "bob"}
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "other_username": "bob"
}
```

**Errors:**
- `400` — Cannot create DM with yourself
- `404` — Target user not found

---

### Get DM Messages

```
GET /api/dms/{dm_id}/messages?since=&limit=
```

**Query parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| since | int | — | Return messages with `id > since` (cursor pagination) |
| limit | int | 50 | Max messages to return |

- Without `since`: returns most recent `limit` messages (oldest first in response).
- With `since`: returns messages after that ID (for polling/long-poll).

**Response:** `200 OK`
```json
{
  "messages": [
    {
      "id": 42,
      "sender_id": 1,
      "sender_username": "alice",
      "content": "Hello!",
      "created_at": "2025-03-15T01:00:00"
    }
  ]
}
```

**Errors:** `404` — DM not found or access denied

---

### Send DM Message

```
POST /api/dms/{dm_id}/messages
```

**Request body:**
```json
{"content": "Hello, world!"}
```

- Content: required, non-empty after trim, max 64KB, UTF-8 (unicode/emoji supported).

**Response:** `200 OK`
```json
{
  "id": 42,
  "sender_id": 1,
  "sender_username": "alice",
  "content": "Hello, world!",
  "created_at": "2025-03-15T01:00:00"
}
```

**Errors:** `400` — Content empty or too long; `404` — DM not found

---

## Chat Rooms

### List Rooms

```
GET /api/rooms
```

Returns rooms the current user is a member of.

**Response:** `200 OK`
```json
[
  {"id": 1, "name": "general", "role": "admin"},
  {"id": 2, "name": "family", "role": "member"}
]
```

---

### Create Room

```
POST /api/rooms
```

Creator is added as room admin.

**Request body:**
```json
{"name": "general"}
```

**Response:** `200 OK`
```json
{"id": 1, "name": "general"}
```

**Errors:** `409` — Room name already exists

---

### Get Room Details

```
GET /api/rooms/{room_id}
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "name": "general",
  "created_at": "2025-03-15T01:00:00",
  "members": [
    {"id": 1, "username": "alice", "role": "admin"},
    {"id": 2, "username": "bob", "role": "member"}
  ]
}
```

**Errors:** `404` — Room not found or not a member

---

### Update Room Members

```
PUT /api/rooms/{room_id}/members
```

**Auth:** Room admin only.

**Request body:**
```json
{
  "add": ["charlie", "dave"],
  "remove": ["eve"]
}
```

- `add` / `remove`: lists of usernames. Omitted keys treated as empty arrays.

**Response:** `200 OK`
```json
{"ok": true}
```

**Errors:** `403` — Not room admin

---

### Get Room Messages

```
GET /api/rooms/{room_id}/messages?since=&limit=
```

Same semantics as DM messages.

**Response:** `200 OK`
```json
{"messages": [...]}
```

**Errors:** `404` — Room not found or not a member

---

### Send Room Message

```
POST /api/rooms/{room_id}/messages
```

**Request body:**
```json
{"content": "Hello, everyone!"}
```

**Response:** `200 OK` — Same shape as send DM message.

**Errors:** `400` — Content empty/too long; `404` — Room not found or not a member

---

## Admin Endpoints

All admin endpoints require an admin user (first registered user or `ADMIN_USERNAME` env).

### Get Config

```
GET /api/admin/config
```

**Response:** `200 OK`
```json
{
  "database_path": "./conduit.db",
  "port": 8080,
  "serve_web_app": true,
  "origin": "*"
}
```

---

### Get Connections

```
GET /api/admin/connections
```

**Response:** `200 OK`
```json
{"websocket": 3}
```

---

### List All Rooms

```
GET /api/admin/rooms
```

**Response:** `200 OK`
```json
[
  {"id": 1, "name": "general", "member_count": 5},
  {"id": 2, "name": "family", "member_count": 4}
]
```

---

### List Users

```
GET /api/admin/users
```

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "username": "alice",
    "is_bot": false,
    "uses_default_password": false
  },
  {
    "id": 2,
    "username": "helper-bot",
    "is_bot": true,
    "uses_default_password": null
  }
]
```

---

### Create User

```
POST /api/admin/users
```

**Request body:**
```json
{"username": "helper-bot", "is_bot": true}
```

For humans: `is_bot: false`. Server assigns default password from `DEFAULT_PASSWORD`.

For bots: `is_bot: true`. Server generates `api_token`; **returned once** in response. Store it securely; it cannot be retrieved later.

**Response:** `200 OK`
```json
{
  "id": 2,
  "username": "helper-bot",
  "is_bot": true,
  "api_token": "xYz123..."
}
```

For human users, `api_token` is `null`.

**Errors:**
- `409` — Username already exists
- `503` — `DEFAULT_PASSWORD` not set (when creating human)
