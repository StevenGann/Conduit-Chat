# Configuration

Conduit Chat is configured via environment variables. A `.env` file in the working directory is loaded automatically (when using pydantic-settings).

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_PATH` | No | `./conduit.db` | Path to SQLite database file |
| `SECRET_KEY` | Yes* | — | JWT signing key; min 32 chars recommended. Required for `/api/setup` and login |
| `DEFAULT_PASSWORD` | Yes* | — | Password assigned to new human users. Required for human user creation |
| `PORT` | No | `8080` | Port for uvicorn (when run directly; Docker may override) |
| `SERVE_WEB_APP` | No | `false` | If true, serve static web app at `/` |
| `WEB_APP_PATH` | No | `./static` | Path to web app static files (used when `SERVE_WEB_APP=true`) |
| `ADMIN_USERNAME` | No | — | Username that is always admin; otherwise first user is admin |
| `ADMIN_PASSWORD` | No | — | If set with `ADMIN_USERNAME` and no users exist, auto-creates first admin on startup |
| `ORIGIN` | No | `*` | CORS allowed origins; comma-separated for multiple |

\* `SECRET_KEY` and `DEFAULT_PASSWORD` are required for setup and for creating human users. Bots can be created without `DEFAULT_PASSWORD`.

## Example .env

```env
DATABASE_PATH=./conduit.db
SECRET_KEY=your-secret-key-at-least-32-characters-long
DEFAULT_PASSWORD=change-me-on-first-login
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-admin-password
PORT=8080
SERVE_WEB_APP=true
WEB_APP_PATH=../web
ORIGIN=http://localhost:3000,https://chat.example.com
```

**Auto-bootstrap:** If `ADMIN_USERNAME` and `ADMIN_PASSWORD` are set and no users exist, the server creates the first admin on startup. No manual `/api/setup` call needed.

## Docker

For Docker Compose, set variables in `docker-compose.yml` or an `.env` file in the same directory:

```yaml
environment:
  - DATABASE_PATH=/app/data/conduit.db
  - SECRET_KEY=${SECRET_KEY}
  - DEFAULT_PASSWORD=${DEFAULT_PASSWORD}
  - SERVE_WEB_APP=true
  - WEB_APP_PATH=/app/static
```

## Production Checklist

- [ ] Set a strong, unique `SECRET_KEY`
- [ ] Set a secure `DEFAULT_PASSWORD` and require users to change it
- [ ] Restrict `ORIGIN` to your actual frontend origin(s)
- [ ] Use HTTPS in production; WebSocket will use `wss://`
- [ ] Ensure `DATABASE_PATH` points to a persistent volume
