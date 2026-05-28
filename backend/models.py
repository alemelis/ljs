from pydantic import BaseModel
from typing import Optional


class AddTorrentRequest(BaseModel):
    magnet: Optional[str] = None
    download_url: Optional[str] = None
    title: Optional[str] = None


class SearchResult(BaseModel):
    title: str
    size: int
    size_human: str
    seeders: int
    leechers: int
    magnet_url: Optional[str] = None
    download_url: Optional[str] = None
    indexer: str
    categories: list[str] = []


class TorrentFile(BaseModel):
    id: int
    name: str
    size: int
    mime_type: Optional[str] = None
    short_name: Optional[str] = None


class Torrent(BaseModel):
    id: int
    name: str
    size: int
    status: str
    progress: float
    download_speed: int
    upload_speed: int
    seeds: int
    peers: int
    eta: int
    files: list[TorrentFile] = []
    active: bool


class SyncJob(BaseModel):
    torrent_id: int
    torrent_name: str
    status: str  # pending | running | completed | failed
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    error: Optional[str] = None
