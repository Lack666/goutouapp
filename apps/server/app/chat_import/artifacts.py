"""Opaque, immutable temporary upload storage, independent of HTTP and SQL."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import BinaryIO, Protocol
from uuid import uuid4

_KEY = re.compile(r"[0-9a-f]{32}\Z")
CHUNK_BYTES = 64 * 1024


class ArtifactStoreError(Exception):
    """An artifact is missing, invalid, or could not be stored."""


class UploadTooLarge(Exception):
    """The request or file exceeds the configured import upload limit."""


@dataclass(frozen=True)
class ArtifactStat:
    key: str
    size_bytes: int
    content_hash: str


class ArtifactWriter(Protocol):
    def write(self, chunk: bytes) -> None: ...
    def finish(self) -> ArtifactStat: ...
    def abort(self) -> None: ...


class ImportArtifactStore(Protocol):
    def begin(self, key: str | None = None) -> ArtifactWriter: ...
    def open(self, key: str) -> BinaryIO: ...
    def stat(self, key: str) -> os.stat_result: ...
    def delete(self, key: str) -> None: ...
    def exists(self, key: str) -> bool: ...
    def cleanup_expired(self, live_keys: set[str], before: datetime) -> int: ...


class _LocalWriter:
    def __init__(self, store: LocalFilesystemImportArtifactStore, key: str) -> None:
        self._store = store
        self._key = key
        self._path = store._path(key, partial=True)
        self._file = self._path.open("xb")
        self._hash = sha256()
        self._size = 0
        self._done = False

    def write(self, chunk: bytes) -> None:
        if self._done or not isinstance(chunk, bytes):
            raise ArtifactStoreError
        self._file.write(chunk)
        self._hash.update(chunk)
        self._size += len(chunk)

    def finish(self) -> ArtifactStat:
        if self._done:
            raise ArtifactStoreError
        self._file.flush()
        os.fsync(self._file.fileno())
        self._file.close()
        final = self._store._path(self._key)
        try:
            # Atomic exclusive publication on the same filesystem. A check
            # followed by POSIX rename could overwrite a concurrent final file.
            os.link(self._path, final)
        except OSError as exc:
            self.abort()
            raise ArtifactStoreError from exc
        self._path.unlink()
        self._done = True
        return ArtifactStat(self._key, self._size, self._hash.hexdigest())

    def abort(self) -> None:
        if not self._file.closed:
            self._file.close()
        self._done = True
        self._path.unlink(missing_ok=True)


class LocalFilesystemImportArtifactStore:
    """The configured root is private server storage, never a static route."""

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str, *, partial: bool = False) -> Path:
        if not _KEY.fullmatch(key):
            raise ArtifactStoreError
        return self._root / f"{key}.{'part' if partial else 'bin'}"

    def begin(self, key: str | None = None) -> ArtifactWriter:
        return _LocalWriter(self, key or uuid4().hex)

    def open(self, key: str) -> BinaryIO:
        path = self._path(key)
        if path.is_symlink():
            raise ArtifactStoreError
        try:
            flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
            return os.fdopen(os.open(path, flags), "rb")
        except OSError as exc:
            raise ArtifactStoreError from exc

    def stat(self, key: str) -> os.stat_result:
        path = self._path(key)
        if path.is_symlink():
            raise ArtifactStoreError
        try:
            return path.stat()
        except OSError as exc:
            raise ArtifactStoreError from exc

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.is_symlink():
            raise ArtifactStoreError
        path.unlink(missing_ok=True)

    def exists(self, key: str) -> bool:
        path = self._path(key)
        return path.is_file() and not path.is_symlink()

    def cleanup_expired(self, live_keys: set[str], before: datetime) -> int:
        """Reap unreferenced completed or interrupted files after the grace period."""
        removed = 0
        for path in self._root.iterdir():
            if path.is_symlink() or path.suffix not in {".bin", ".part"}:
                continue
            if not _KEY.fullmatch(path.stem) or path.stem in live_keys:
                continue
            if path.stat().st_mtime < before.timestamp():
                path.unlink(missing_ok=True)
                removed += 1
        return removed
