"""Serialize local file operations with an exclusive advisory lock.

Use ``exclusive_file_lock`` around publication or artifact updates that share
a sentinel file. Windows locks one byte; Unix uses flock. Callers must use
the same lock path to coordinate their writes.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO


def _is_windows() -> bool:
    return sys.platform == "win32"


def _ensure_lock_byte(handle: BinaryIO) -> None:
    handle.seek(0)
    if handle.read(1) == b"":
        handle.seek(0)
        handle.write(b"\0")
    handle.seek(0)


def _acquire(handle: BinaryIO) -> None:
    if _is_windows():
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        return

    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)


def _release(handle: BinaryIO) -> None:
    if _is_windows():
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        return

    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def exclusive_file_lock(path: str | Path) -> Iterator[BinaryIO]:
    """Hold a lock on a sentinel file for the duration of a ``with`` block.

    Yield the open binary handle. Release the lock and close the handle when
    the block exits, including when its body raises an exception.
    """
    lock_path = Path(path).expanduser().resolve()
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(lock_path, flags, 0o600)
    with os.fdopen(descriptor, "r+b", buffering=0) as handle:
        _ensure_lock_byte(handle)
        _acquire(handle)
        try:
            yield handle
        finally:
            _release(handle)
