from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .database import init_db
from .routers import admin, auth, dms, rooms, setup, ws
from .websocket import manager as ws_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    Path(settings.database_path).parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(settings.database_path)
    await init_db(conn)
    await conn.close()
    yield


app = FastAPI(
    title="Conduit Chat",
    description="Self-hosted private chat for family and AI agents",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origin.split(",") if "," in settings.origin else [settings.origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(setup.router)
app.include_router(auth.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(dms.router, prefix="/api")
app.include_router(rooms.router, prefix="/api")
app.include_router(ws.router)


@app.get("/health")
async def health():
    return {"status": "ok"}


if settings.serve_web_app:
    web_path = Path(settings.web_app_path)
    if web_path.exists():
        app.mount("/", StaticFiles(directory=str(web_path), html=True), name="web")
