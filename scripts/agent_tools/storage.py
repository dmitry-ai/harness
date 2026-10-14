"""Durable single-file writes and cooperative, process-safe locks."""

from contextlib import contextmanager
import os
from pathlib import Path
import tempfile
import time


def data_dir_for(path: Path) -> Path:
    """Locate project-owned service storage; never put mutable state in .agents."""
    resolved = Path(path).resolve()
    start = resolved if not resolved.exists() or resolved.is_dir() else resolved.parent
    for parent in (start, *start.parents):
        if parent.name == 'ꘖ':
            return parent / 'data'
        if (parent / 'ꘖ').is_dir():
            return parent / 'ꘖ' / 'data'
        if parent.name == '.agents':
            return parent.parent / 'ꘖ' / 'data'
        if (parent / '.agents').is_dir():
            return parent / 'ꘖ' / 'data'
    return start / 'ꘖ' / 'data'


@contextmanager
def locked(path: Path, timeout: float = 15):
    """OS releases the lock on process death; the persistent lock file is not deleted."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as stream:
        stream.seek(0, os.SEEK_END)
        if not stream.tell():
            stream.write(b'\0')
            stream.flush()
        deadline = time.monotonic() + timeout
        while True:
            try:
                stream.seek(0)
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f'Lock busy: {path}')
                time.sleep(0.05)
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == 'nt':
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def create_bytes(path: Path, data: bytes):
    """Never replace an existing file, including an empty file."""
    with path.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def replace_bytes(path: Path, data: bytes):
    """Atomically replace one owned output; this is not a multi-file transaction."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f'.{path.name}.', dir=path.parent)
    temp = Path(name)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)
