from fastapi import APIRouter, Request
from backend.models import AddTorrentRequest
from backend.config import settings

router = APIRouter()

_synced_ids: set[int] = set()


@router.get("/torrents")
async def list_torrents(request: Request):
    torbox = request.app.state.torbox
    rclone = request.app.state.rclone
    torrents = await torbox.list_torrents()

    if settings.auto_sync:
        for t in torrents:
            tid = t["id"]
            if (t.get("download_finished") or t.get("cached")) and tid not in _synced_ids:
                _synced_ids.add(tid)
                await rclone.start_sync(tid, t["name"])

    return torrents


@router.post("/torrents")
async def add_torrent(request: Request, body: AddTorrentRequest):
    torbox = request.app.state.torbox
    if body.magnet:
        return await torbox.add_torrent(body.magnet)
    if body.download_url:
        filename = (body.title or "download") + ".torrent"
        return await torbox.add_torrent_file(body.download_url, filename)
    from fastapi import HTTPException
    raise HTTPException(400, detail="Either magnet or download_url is required")


@router.delete("/torrents/{torrent_id}")
async def delete_torrent(request: Request, torrent_id: int):
    torbox = request.app.state.torbox
    return await torbox.delete_torrent(torrent_id)
