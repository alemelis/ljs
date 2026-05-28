from fastapi import APIRouter, Request, HTTPException

router = APIRouter()


@router.post("/sync/{torrent_id}")
async def trigger_sync(request: Request, torrent_id: int, torrent_name: str):
    rclone = request.app.state.rclone
    job = await rclone.start_sync(torrent_id, torrent_name)
    return job.to_dict()


@router.get("/sync/status")
async def sync_status(request: Request):
    rclone = request.app.state.rclone
    return rclone.get_all()
