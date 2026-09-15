"""Process-safe archive lock for Windows and macOS/Linux (standard library only)."""
from contextlib import contextmanager
import errno
import os
import time

if os.name == 'nt':
    import msvcrt
else:
    import fcntl


@contextmanager
def file_lock(path, blocking=True, timeout=60):
    with open(path, 'a+b') as handle:
        if os.name == 'nt':
            handle.seek(0, 2)
            if handle.tell() == 0:
                handle.write(b'\0')
                handle.flush()
        deadline = time.monotonic() + timeout
        while True:
            try:
                if os.name == 'nt':
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as exc:
                if exc.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                    raise
                if not blocking or time.monotonic() >= deadline:
                    raise BlockingIOError('Archivio occupato da un’altra operazione. Riprova tra poco.') from exc
                time.sleep(.1)
        try:
            yield
        finally:
            if os.name == 'nt':
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)
