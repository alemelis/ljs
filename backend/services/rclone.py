import asyncio
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Optional
from backend.config import Settings


@dataclass
class SyncJob:
    torrent_id: int
    torrent_name: str
    status: str = "pending"
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    error: Optional[str] = None
    _process: Optional[asyncio.subprocess.Process] = field(default=None, repr=False)

    def to_dict(self) -> dict:
        return {
            "torrent_id": self.torrent_id,
            "torrent_name": self.torrent_name,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "error": self.error,
        }


class RcloneManager:
    def __init__(self, settings: Settings):
        self._remote = settings.rclone_remote_name
        self._config = settings.rclone_config_path
        self._local_storage = settings.local_storage_path
        self._movies_path = settings.movies_path
        self._tv_path = settings.tv_path
        self._other_path = settings.other_path
        self._jobs: dict[int, SyncJob] = {}
        self._media_types: dict[int, str] = {}

    def set_media_type(self, torrent_id: int, media_type: Optional[str]) -> None:
        if media_type:
            self._media_types[torrent_id] = media_type

    async def _find_remote_dir(self, torrent_name: str) -> str:
        """List WebDAV root and find the directory matching torrent_name."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "rclone", "lsf", f"{self._remote}:",
                "--dirs-only", "--config", self._config,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            dirs = [d.rstrip("/").strip() for d in stdout.decode().splitlines() if d.strip()]
        except Exception:
            return torrent_name

        name_lower = torrent_name.lower()
        # exact match first, then suffix match, then substring match
        for d in dirs:
            if d.lower() == name_lower:
                return d
        for d in dirs:
            if d.lower().endswith(name_lower):
                return d
        for d in dirs:
            if name_lower in d.lower():
                return d
        return torrent_name

    async def start_sync(self, torrent_id: int, torrent_name: str) -> SyncJob:
        if torrent_id in self._jobs and self._jobs[torrent_id].status == "running":
            return self._jobs[torrent_id]

        job = SyncJob(
            torrent_id=torrent_id,
            torrent_name=torrent_name,
            status="running",
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        self._jobs[torrent_id] = job

        remote_dir = await self._find_remote_dir(torrent_name)
        remote_path = f"{self._remote}:{remote_dir}"
        media_type = self._media_types.get(torrent_id, "other")
        base = {"movie": self._movies_path, "tv": self._tv_path}.get(media_type, self._other_path)
        local_path = f"{base}/{torrent_name}"

        try:
            proc = await asyncio.create_subprocess_exec(
                "rclone", "copy",
                remote_path, local_path,
                "--config", self._config,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            job._process = proc
        except FileNotFoundError:
            job.status = "failed"
            job.error = "rclone not found in PATH"
            job.finished_at = datetime.now(timezone.utc).isoformat()
            return job

        asyncio.create_task(self._monitor(job, proc))
        return job

    async def _monitor(self, job: SyncJob, proc: asyncio.subprocess.Process):
        _, stderr = await proc.communicate()
        job.finished_at = datetime.now(timezone.utc).isoformat()
        if proc.returncode == 0:
            job.status = "completed"
        else:
            job.status = "failed"
            job.error = stderr.decode(errors="replace").strip()[-500:] if stderr else "unknown error"

    def get_all(self) -> list[dict]:
        return [j.to_dict() for j in self._jobs.values()]

    def get_job(self, torrent_id: int) -> Optional[SyncJob]:
        return self._jobs.get(torrent_id)

    def is_synced(self, torrent_id: int) -> bool:
        job = self._jobs.get(torrent_id)
        return job is not None and job.status == "completed"
