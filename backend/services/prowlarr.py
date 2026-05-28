import httpx
from urllib.parse import quote
from fastapi import HTTPException
from backend.config import Settings


def _human_size(size_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


class ProwlarrClient:
    def __init__(self, settings: Settings):
        self._url = settings.prowlarr_url.rstrip("/")
        self._client = httpx.AsyncClient(
            headers={"X-Api-Key": settings.prowlarr_api_key},
            timeout=30,
        )

    async def search(self, query: str) -> list[dict]:
        try:
            r = await self._client.get(
                f"{self._url}/api/v1/search",
                params={"query": query, "type": "search", "indexerIds": -2, "limit": 20},
            )
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(502, detail=f"Prowlarr error: {e.response.status_code}")
        except httpx.RequestError:
            raise HTTPException(502, detail="Prowlarr unreachable")

        results = []
        for item in r.json():
            size = item.get("size") or 0
            title = item.get("title", "")
            info_hash = item.get("infoHash", "")
            raw_magnet = item.get("magnetUrl") or ""
            download_url = item.get("downloadUrl") or ""

            # Prowlarr proxies magnet links as http:// download URLs; rebuild from infoHash
            if info_hash and not raw_magnet.startswith("magnet:"):
                magnet_url = f"magnet:?xt=urn:btih:{info_hash}&dn={quote(title)}"
            elif raw_magnet.startswith("magnet:"):
                magnet_url = raw_magnet
            else:
                magnet_url = None  # will fall back to torrent file upload

            results.append({
                "title": title,
                "size": size,
                "size_human": _human_size(size),
                "seeders": item.get("seeders") or 0,
                "leechers": item.get("leechers") or 0,
                "magnet_url": magnet_url,
                "download_url": download_url,
                "indexer": item.get("indexer", ""),
                "categories": [c.get("name", "") for c in (item.get("categories") or [])],
            })
        return results

    async def close(self):
        await self._client.aclose()
