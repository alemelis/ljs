import httpx
from fastapi import HTTPException
from backend.config import Settings


class TorBoxClient:
    def __init__(self, settings: Settings):
        self._base = settings.torbox_base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {settings.torbox_api_key}"},
            timeout=30,
        )

    async def add_torrent(self, magnet: str) -> dict:
        try:
            r = await self._client.post(
                f"{self._base}/api/torrents/createtorrent",
                data={"magnet": magnet},
            )
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(502, detail=f"TorBox error: {e.response.status_code} {e.response.text}")
        except httpx.RequestError:
            raise HTTPException(502, detail="TorBox unreachable")
        return r.json()

    async def add_torrent_file(self, url: str, filename: str) -> dict:
        try:
            dl = await self._client.get(url, follow_redirects=True)
            dl.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(502, detail=f"Failed to fetch torrent file: {e.response.status_code}")
        except httpx.RequestError:
            raise HTTPException(502, detail="Could not download torrent file")
        try:
            r = await self._client.post(
                f"{self._base}/api/torrents/createtorrent",
                files={"file": (filename, dl.content, "application/x-bittorrent")},
            )
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(502, detail=f"TorBox error: {e.response.status_code} {e.response.text}")
        except httpx.RequestError:
            raise HTTPException(502, detail="TorBox unreachable")
        return r.json()

    async def list_torrents(self) -> list[dict]:
        try:
            r = await self._client.get(
                f"{self._base}/api/torrents/mylist",
                params={"bypassCache": "true"},
            )
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(502, detail=f"TorBox error: {e.response.status_code}")
        except httpx.RequestError:
            raise HTTPException(502, detail="TorBox unreachable")

        body = r.json()
        data = body.get("data") or []
        if not isinstance(data, list):
            return []

        torrents = []
        for t in data:
            files = []
            for f in (t.get("files") or []):
                files.append({
                    "id": f.get("id", 0),
                    "name": f.get("name", ""),
                    "size": f.get("size", 0),
                    "mime_type": f.get("mimetype"),
                    "short_name": f.get("short_name"),
                })
            torrents.append({
                "id": t.get("id", 0),
                "name": t.get("name", ""),
                "size": t.get("size", 0),
                "status": t.get("download_state", "unknown"),
                "progress": float(t.get("progress", 0)),
                "download_speed": t.get("download_speed", 0),
                "upload_speed": t.get("upload_speed", 0),
                "seeds": t.get("seeds", 0),
                "peers": t.get("peers", 0),
                "eta": t.get("eta", 0),
                "files": files,
                "active": t.get("active", False),
                "download_finished": t.get("download_finished", False),
                "cached": t.get("cached", False),
            })
        return torrents

    async def delete_torrent(self, torrent_id: int) -> dict:
        try:
            r = await self._client.post(
                f"{self._base}/api/torrents/controltorrent",
                json={"torrent_id": torrent_id, "operation": "delete"},
            )
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(502, detail=f"TorBox error: {e.response.status_code}")
        except httpx.RequestError:
            raise HTTPException(502, detail="TorBox unreachable")
        return r.json()

    async def close(self):
        await self._client.aclose()
