# Data Model

Reference for developers and AI agents integrating with Conduit Chat.

## Entities

### User

| Field | Type | Description |
|-------|------|-------------|
| id | int | Primary key |
| username | string | Unique, used for login and display |
| password_hash | string \| null | Bcrypt hash; null for bots |
| is_bot | bool | true = bot (uses api_token), false = human (uses password) |
| api_token | string \| null | Unique token for bots; shown once on creation |
| uses_default_password | bool | Human only; true until password changed |
| created_at | string | SQLite datetime (UTC) |

### DM Conversation

| Field | Type | Description |
|-------|------|-------------|
| id | int | Primary key |
| user1_id | int | Lower user id (user1_id < user2_id) |
| user2_id | int | Higher user id |
| created_at | string | SQLite datetime |

Unique constraint on `(user1_id, user2_id)`.

### Room

| Field | Type | Description |
|-------|------|-------------|
| id | int | Primary key |
| name | string | Unique room name |
| created_at | string | SQLite datetime |

### Room Member

| Field | Type | Description |
|-------|------|-------------|
| room_id | int | FK to rooms |
| user_id | int | FK to users |
| role | string | `"admin"` or `"member"` |

Creator is admin; only admins can add/remove members.

### Message

| Field | Type | Description |
|-------|------|-------------|
| id | int | Primary key, monotonic |
| conversation_type | string | `"dm"` or `"room"` |
| conversation_id | int | dm_conversations.id or rooms.id |
| sender_id | int | FK to users |
| content | string | UTF-8 text, max 64KB |
| created_at | string | SQLite datetime |

## Message Pagination

- `GET .../messages` without `since`: returns latest N messages, ordered by id ascending.
- `GET .../messages?since=M`: returns messages with `id > M`, ordered by id ascending.

Use the largest `id` from a batch as `since` for the next request.

## IDs and References

- All IDs are integers.
- `conversation_id` in messages matches `dm_conversations.id` when `conversation_type="dm"`, or `rooms.id` when `conversation_type="room"`.
