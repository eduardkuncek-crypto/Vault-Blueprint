"""
notelock.py — one lock and one safe write, shared by everything that touches
a daily note.

WHY THIS EXISTS

More than one script writes to `Calendar/Daily/YYYY-MM-DD.md`, and one of
them (`logchange.py`) writes to it on every single vault write. Without
coordination, two writers doing read-modify-write on the same file is a
textbook lost update:

    lines = p.read_text().split("\n")   # <- another process writes here
    ...
    p.write_text("\n".join(lines))      # <- and this clobbers it

This has actually happened to a vault built on this design: twenty parallel
writes to one daily note reduced it from 13,655 bytes to 5,176, then to
4,404 on a second run — a whole section gone, dozens of change-log lines
gone, the file ending mid-word. Exit code 0 every time, because nothing
raised — it just silently wrote the wrong thing.

A lock in one script alone doesn't fix it, because the other script writing
the same file is still unlocked. Every writer has to take the same lock,
which is why this is one shared module rather than a lock built into each
script separately.

WHAT IT GIVES YOU

    with locked(path):
        text = path.read_text(encoding="utf-8")
        ...
        write_atomic(path, new_text)

`locked()`  — an advisory exclusive lock (`fcntl.flock`) held on a sidecar
              `.lock` file, so it survives `os.replace()` swapping the note's
              inode. Blocks; the critical section is milliseconds.
`write_atomic()` — writes a temp file in the same directory and `os.replace()`s
              it into position. `os.replace` is atomic on POSIX, so a reader
              sees either the whole old file or the whole new one, never a
              half-written one. `Path.write_text` truncates first and is the
              reason torn writes were possible at all.

Dropbox-style sync is not a distributed lock. This protects against two
processes on THIS machine. Two machines editing the same daily note in the
same second is a different problem — that's what a sync client's own
conflict-copy mechanism is for.

Windows note: `fcntl` is POSIX-only. On Windows this degrades to no locking
at all (see the try/except below) rather than crashing — a missed lock is
recoverable (rare collision, sync conflict file), an ImportError on every
script that touches a daily note is not.

No dependencies. Plain stdlib.
"""
import hashlib
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

try:
    import fcntl
    _HAVE_FCNTL = True
except ImportError:
    _HAVE_FCNTL = False

__all__ = ["locked", "write_atomic"]


def _lock_file(p: Path) -> Path:
    """Where a note's lock lives: the system temp dir, never the vault.

    Keyed by a hash of the absolute path so two different notes never
    collide and the same note always maps to the same lock."""
    key = hashlib.sha256(str(p.resolve()).encode("utf-8")).hexdigest()[:16]
    d = Path(tempfile.gettempdir()) / "aios-notelock"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{key}.lock"


@contextmanager
def locked(path):
    """Hold an exclusive advisory lock for the duration of the block.

    On a platform without fcntl (Windows), this is a no-op context manager —
    concurrent writes there are rarer (no hourly cron writing the same file
    from a second process in most single-machine setups) and a missing lock
    is a better failure mode than every daily-note script refusing to run.
    """
    if not _HAVE_FCNTL:
        yield
        return
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    lock = _lock_file(p)
    fh = open(lock, "w")
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        finally:
            fh.close()


def write_atomic(path, body: str) -> None:
    """Replace a file's contents atomically. Never leaves a partial file."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + f".tmp{os.getpid()}")
    try:
        tmp.write_text(body, encoding="utf-8")
        os.replace(tmp, p)
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise
