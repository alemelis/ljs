from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from backend.config import settings
from backend.services.prowlarr import ProwlarrClient
from backend.services.torbox import TorBoxClient
from backend.services.rclone import RcloneManager
from backend.routers import search, torrents, sync


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.prowlarr = ProwlarrClient(settings)
    app.state.torbox = TorBoxClient(settings)
    app.state.rclone = RcloneManager(settings)
    yield
    await app.state.prowlarr.close()
    await app.state.torbox.close()


app = FastAPI(title="Long John Silver", lifespan=lifespan)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router, prefix="/api")
app.include_router(torrents.router, prefix="/api")
app.include_router(sync.router, prefix="/api")

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
