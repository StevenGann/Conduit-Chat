# Conduit Chat Server

Backend server for Conduit Chat. Fully Docker containerized. Can optionally serve the web app.

## Quick Start (Local)

```bash
cd server
pip install -r requirements.txt

# Create .env or set env vars
export SECRET_KEY="your-secret-key-min-32-chars"
export DEFAULT_PASSWORD="default-password-for-new-users"

# Run server
uvicorn conduit.main:app --reload --port 8080

# With web app (serve from sibling web/ folder; run from server/)
export SERVE_WEB_APP=true
export WEB_APP_PATH=../web
# From server/ directory:
uvicorn conduit.main:app --reload --port 8080
```

## First-Time Setup

1. Start the server
2. POST to `/api/setup` with `{"username": "admin", "password": "your-password"}` to create the first admin user
3. Log in at the web app or via `POST /api/auth/login`

## Docker

```bash
# From repo root
docker-compose -f server/docker-compose.yml up -d

# With env file
SECRET_KEY=xxx DEFAULT_PASSWORD=yyy docker-compose -f server/docker-compose.yml up -d
```

## API

- `POST /api/setup` - Bootstrap first admin (when no users exist)
- `POST /api/auth/login` - Login (returns JWT + `requires_password_change`)
- `PUT /api/auth/change-password` - Change password
- `GET /api/dms` - List DMs
- `POST /api/dms` - Create/find DM (`{"target_username": "..."}`)
- `GET /api/dms/{id}/messages` - Get messages
- `POST /api/dms/{id}/messages` - Send message
- `GET /api/rooms` - List rooms
- `POST /api/rooms` - Create room
- `GET /api/rooms/{id}` - Room details
- `PUT /api/rooms/{id}/members` - Add/remove members
- `GET /api/rooms/{id}/messages` - Get messages
- `POST /api/rooms/{id}/messages` - Send message
- `WS /ws?token=...` - WebSocket for real-time updates
- `GET /api/admin/*` - Admin endpoints (config, users, rooms, connections)

## Documentation

See [../docs/](../docs/) for full API reference, authentication, WebSocket protocol, and integration examples. Key files:

- [docs/API.md](../docs/API.md) — REST API reference
- [docs/AUTHENTICATION.md](../docs/AUTHENTICATION.md) — Auth for humans and bots
- [docs/WEBSOCKET.md](../docs/WEBSOCKET.md) — Real-time protocol
- [docs/INTEGRATION.md](../docs/INTEGRATION.md) — Python, cURL, and bot examples
- [docs/llms.txt](../docs/llms.txt) — Compact summary for AI agents

## Planned

- MCP endpoint and tools for AI agent integration
- Webhook registration for external notifications
- Dashboard UI for admin (API exists)
