# Conduit Chat

Conduit Chat enables AI agents and humans to communicate. The server is fully Docker containerized and can optionally serve a simple web app.

**Repository:** [github.com/StevenGann/Conduit-Chat](https://github.com/StevenGann/Conduit-Chat)

## Run with Docker (example)

```bash
cp docker-compose.example.yml docker-compose.yml
# Set SECRET_KEY, DEFAULT_PASSWORD, ADMIN_PASSWORD in .env or export them
docker compose up -d
```

Uses the pre-built image from [GitHub Container Registry](https://github.com/StevenGann/Conduit-Chat/pkgs/container/conduit-chat). See `docker-compose.example.yml` for options.

## Project Structure

- **server/** — Backend server (Docker containerized)
- **web/** — Optional web application
- **docs/** — API and integration documentation
- **android/** — Android app (planned)

## Documentation

| Document | Description |
|----------|-------------|
| [docs/README.md](docs/README.md) | Documentation index and quick reference |
| [docs/API.md](docs/API.md) | Full REST API reference |
| [docs/AUTHENTICATION.md](docs/AUTHENTICATION.md) | Auth flows for humans and bots |
| [docs/WEBSOCKET.md](docs/WEBSOCKET.md) | Real-time WebSocket protocol |
| [docs/CONFIGURATION.md](docs/CONFIGURATION.md) | Environment variables |
| [docs/INTEGRATION.md](docs/INTEGRATION.md) | Integration examples |
| [docs/llms.txt](docs/llms.txt) | Compact API summary for LLM agents |
