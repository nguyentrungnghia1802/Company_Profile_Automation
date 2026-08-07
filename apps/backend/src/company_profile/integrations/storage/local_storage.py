"""Local filesystem ObjectStorage adapter."""

from __future__ import annotations

from pathlib import Path


class LocalObjectStorage:
    """Object storage adapter backed by local filesystem storage root."""

    def __init__(self, storage_root: str = "./data/storage") -> None:
        self.root_path = Path(storage_root)
        self.root_path.mkdir(parents=True, exist_ok=True)

    async def put_object(
        self,
        key: str,
        data: bytes,
        content_type: str = "text/plain",  # noqa: ARG002
    ) -> str:
        """Store bytes at relative storage key."""
        target_path = self.root_path / key
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(data)
        return str(target_path)

    async def get_object(self, key: str) -> bytes:
        """Retrieve stored object bytes."""
        target_path = self.root_path / key
        if not target_path.exists():
            raise FileNotFoundError(f"Storage object not found: {key}")
        return target_path.read_bytes()

    async def generate_signed_url(self, key: str, expiry_seconds: int = 300) -> str:
        """Generate local access URL."""
        return f"/api/v1/storage/download?key={key}&expiry={expiry_seconds}"
