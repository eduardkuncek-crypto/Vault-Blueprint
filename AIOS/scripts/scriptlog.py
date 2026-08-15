#!/usr/bin/env python3
"""
scriptlog.py — every AIOS script's run history, automatically, as a real note.

Import this once near the top of a script:

    import scriptlog

Nothing else needed. On import it starts capturing this process's
stdout/stderr; when the process exits (success, error, or crash) it appends
one entry to `AIOS/history/scripts/<script-name>.md` — a proper Markdown
note, one per script, newest run at the bottom: timestamp, args, how long it
ran, whether it succeeded, and everything it printed (fenced as code, so a
script's own output can never corrupt the note's structure).

One note per script, not one shared file — several scripts can run on
independent schedules, and one shared file under concurrent writes is a
corruption risk that per-script files avoid.

Cost: stdlib only, one file open+append at process exit. Negligible.

Limitation: `sys.exit(n)` with n != 0 is recorded as OK (Python doesn't route
SystemExit through excepthook) unless the script raises an actual exception.
Crashes and uncaught exceptions are always caught correctly.
"""
import sys
import io
import atexit
import time
from pathlib import Path
from datetime import datetime

_HISTORY_DIR = Path(__file__).resolve().parent.parent / "history" / "scripts"
_SCRIPT_NAME = Path(sys.argv[0]).stem if sys.argv and sys.argv[0] else "interactive"
_START = time.time()
_ARGS = sys.argv[1:]
_EXC = {}


class _Tee(io.TextIOBase):
    def __init__(self, real, buf):
        self._real = real
        self._buf = buf

    def write(self, s):
        self._buf.write(s)
        return self._real.write(s)

    def flush(self):
        self._real.flush()


_out_buf = io.StringIO()
_err_buf = io.StringIO()
_orig_stdout, _orig_stderr = sys.stdout, sys.stderr
sys.stdout = _Tee(_orig_stdout, _out_buf)
sys.stderr = _Tee(_orig_stderr, _err_buf)

_orig_excepthook = sys.excepthook


def _excepthook(exc_type, exc, tb):
    _EXC["type"] = exc_type
    _EXC["value"] = exc
    _orig_excepthook(exc_type, exc, tb)


sys.excepthook = _excepthook


def _header(name):
    return (
        "---\n"
        f"title: {name} — run history\n"
        "tags:\n"
        "  - generated\n"
        "---\n\n"
        f"# {name} — run history\n\n"
        "> [!info] Generated — do not edit by hand\n"
        f"> Appended by `scriptlog.py` every time `{name}.py` runs. "
        "Newest run at the bottom.\n\n"
        "## Runs\n"
    )


def _write_entry():
    sys.stdout, sys.stderr = _orig_stdout, _orig_stderr
    dur = time.time() - _START
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if "type" in _EXC:
        status = f"ERROR: {_EXC['type'].__name__}: {_EXC['value']}"
    else:
        status = "OK"
    out = _out_buf.getvalue().strip()
    err = _err_buf.getvalue().strip()
    try:
        _HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        note_path = _HISTORY_DIR / f"{_SCRIPT_NAME}.md"
        is_new = not note_path.exists()
        entry = [f"\n### {ts} — {status} ({dur:.2f}s)\n\n"]
        entry.append(f"args: `{_ARGS}`\n\n")
        if out:
            entry.append("```text\n" + out + "\n```\n")
        else:
            entry.append("_no output_\n")
        if err:
            entry.append("\nstderr:\n```text\n" + err + "\n```\n")
        with open(note_path, "a", encoding="utf-8") as f:
            if is_new:
                f.write(_header(_SCRIPT_NAME))
            f.write("".join(entry))
    except Exception:
        pass  # logging must never break the script it's watching


atexit.register(_write_entry)
