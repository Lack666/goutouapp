"""OS-owned fence: losing a DB connection does not prove a worker stopped."""

import os
from pathlib import Path


def _lock(file):
    file.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl

        fcntl.flock(file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


class WorkerFence:
    def __init__(self, path: Path):
        self.path = path
        self.file = path.open("xb+")
        try:
            self.file.write(b"0")
            self.file.flush()
            _lock(self.file)
        except BaseException:
            self.file.close()
            path.unlink(missing_ok=True)
            raise

    def close(self):
        self.file.close()
        self.path.unlink(missing_ok=True)


def is_live(path: Path):
    if not path.exists():
        return False
    if path.is_symlink():
        raise OSError("Invalid fence storage")
    with path.open("r+b") as file:
        try:
            _lock(file)
        except BlockingIOError:
            return True
        except OSError as exc:
            if os.name == "nt" and exc.errno in {13, 11}:
                return True
            raise
    return False
