#!/usr/bin/env python3
"""
scheduler.py — install/remove a recurring background job, on whatever OS this
is running on. One shared implementation so every script that needs "run me
every N minutes" (backup-cowork.py, vault-snapshot.py, changelog-check.py)
does it the same way instead of each hand-rolling `crontab` calls that only
work on Linux.

Why this exists
----------------
The very first version of this vault's automation only knew how to write a
crontab line. That works on Linux and (usually) macOS, and does nothing at
all on Windows — no error, no warning, the install step just silently has no
effect, because `crontab` isn't a Windows program. Someone on Windows would
have every OTHER part of the setup succeed and never find out their chats
were never actually being backed up.

This module picks the right mechanism for the OS it's running on:

  - Linux / macOS  -> cron, via the `crontab` command
  - Windows        -> Task Scheduler, via the `schtasks` command
  - Anything else, or the tool is missing -> reports that clearly instead of
    pretending it worked. A script that can't schedule itself should say so,
    not lie about it.

Every job installed through this module is tagged `AIOS_<name>` so it can be
found and removed again without touching anything the user set up themselves.

Known limitation: the tag is scoped to the job NAME (`backup-cowork`,
`vault-snapshot`, `changelog-check`), not to which vault it belongs to. If you
run setup on two different vault copies on the same machine, the second one
will overwrite the first's schedule under the same name — this module isn't
multi-vault-aware. For the common case (one person, one vault, one machine)
that's never an issue; `is_installed()` still correctly detects and fixes a
STALE entry left over from a moved/renamed/re-copied vault, which is the
failure this was actually built to catch.

Usage (as a library — this is what the other scripts do):

    import scheduler
    ok, detail = scheduler.install("backup-cowork", SCRIPT_PATH, every_minutes=60)
    ok, detail = scheduler.uninstall("backup-cowork")
    installed  = scheduler.is_installed("backup-cowork")
    tool, why  = scheduler.available()

Usage (from a terminal, mostly for the setup-check report):

    python3 AIOS/scripts/scheduler.py --status
    python3 AIOS/scripts/scheduler.py --install backup-cowork --script <path> --every-min 60
    python3 AIOS/scripts/scheduler.py --uninstall backup-cowork

No dependencies. Plain stdlib.
"""
import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path

TAG_PREFIX = "AIOS_"


def _cron_schedule(every_minutes: int) -> tuple:
    """Turn "every N minutes" into a cron field expression that's actually
    correct, plus a human-readable cadence string.

    Two cases, because a minute field only holds 0-59:

      - N is a whole number of hours (60, 120, ...) -> hour-based cron
        (`0 */H * * *`), never `*/60`, which is meaningless in a field that
        wraps at 60 and would either error or silently fire every minute
        depending on the cron implementation.
      - Anything else -> `*/M * * * *`, where M is rounded to the nearest
        divisor of 60 that's <= 30. A non-dividing interval like `*/7`
        fires at :00 :07 ... :49 :56 and then waits 4 minutes — not what
        "every 7 minutes" means to anyone.
    """
    n = max(1, every_minutes)
    if n >= 60:
        hours = max(1, min(23, round(n / 60)))
        return f"0 */{hours} * * *", f"every {hours}h"

    m = max(1, min(30, n))
    if 60 % m != 0:
        for c in (1, 2, 3, 4, 5, 6, 10, 12, 15, 20, 30):
            if c >= m:
                m = c
                break
        else:
            m = 30
    return f"*/{m} * * * *", f"every {m} min"


def available():
    """Which scheduling tool this OS actually has. Returns (tool, detail).

    tool is one of "cron", "schtasks", or None. Never guesses — only reports
    a tool as available if the command genuinely exists on PATH.
    """
    system = platform.system()
    if system == "Windows":
        if shutil.which("schtasks"):
            return "schtasks", "Windows Task Scheduler"
        return None, "schtasks.exe not found — Task Scheduler should ship with " \
                      "every Windows install; something unusual is going on"
    # Linux, macOS, and anything else POSIX-flavoured
    if shutil.which("crontab"):
        return "cron", "cron"
    if system == "Darwin":
        return None, "cron is not available. Install it isn't really a thing on " \
                      "macOS any more — use System Settings > General > Login " \
                      "Items, or run the script by hand when you think of it"
    return None, "'crontab' is not installed. On Debian/Ubuntu/Mint: sudo apt " \
                 "install cron. On Fedora: sudo dnf install cronie"


def _job_name(name: str) -> str:
    return f"{TAG_PREFIX}{name}"


# ---------------------------------------------------------------- cron (Linux/macOS)


def _cron_read() -> str:
    r = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


def _cron_strip(text: str, tag: str) -> str:
    out, drop_next = [], False
    marker = f"# {tag}"
    for line in text.splitlines():
        if line.strip() == marker:
            drop_next = True
            continue
        if drop_next:
            drop_next = False
            continue
        out.append(line)
    return "\n".join(out).strip()


def _cron_install(name, command, every_minutes) -> tuple:
    tag = _job_name(name)
    fields, cadence = _cron_schedule(every_minutes)
    line = f"{fields} {command}"
    new = (_cron_strip(_cron_read(), tag) + f"\n\n# {tag}\n{line}\n").strip() + "\n"
    r = subprocess.run(["crontab", "-"], input=new, text=True, capture_output=True)
    if r.returncode != 0:
        return False, f"crontab install failed: {r.stderr.strip()}"
    return True, f"cron: {cadence}"


def _cron_uninstall(name) -> tuple:
    tag = _job_name(name)
    new = _cron_strip(_cron_read(), tag)
    r = subprocess.run(["crontab", "-"], input=new + "\n", text=True,
                       capture_output=True)
    if r.returncode != 0:
        return False, f"crontab update failed: {r.stderr.strip()}"
    return True, "removed"


def _cron_is_installed(name, script_path=None) -> bool:
    """True only if a job tagged for this name exists AND (when script_path
    is given) its command line actually points at this script.

    Matching on the tag alone is a real bug, found by testing: copy or move
    the vault, or have an old crontab entry left over from a different copy
    of it, and a same-named tag from the WRONG vault makes this return True —
    so the caller skips installing the right one, and the right vault's
    automation silently never gets scheduled. The tag says "a job with this
    name exists somewhere"; the path check says "and it's THIS vault's job".
    """
    marker = f"# {_job_name(name)}"
    lines = _cron_read().splitlines()
    for i, line in enumerate(lines):
        if line.strip() != marker:
            continue
        if script_path is None:
            return True
        # The next non-blank line is the actual cron entry for this tag.
        for later in lines[i + 1:]:
            if later.strip():
                return str(script_path) in later
            break
    return False


# ---------------------------------------------------------------- schtasks (Windows)


def _schtasks_install(name, python_exe, script_path, args, every_minutes) -> tuple:
    tn = _job_name(name)
    # Task Scheduler's MINUTE schedule takes a plain minute count — no need
    # to round to a divisor of 60, that's a cron-only quirk (cron's minute
    # field wraps at 60; schtasks just counts minutes since it started).
    m = max(1, every_minutes)
    arg_str = " ".join(f'"{a}"' for a in args)
    tr = f'"{python_exe}" "{script_path}" {arg_str}'.strip()
    cmd = ["schtasks", "/Create", "/SC", "MINUTE", "/MO", str(m),
           "/TN", tn, "/TR", tr, "/F"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return False, f"schtasks failed: {(r.stderr or r.stdout).strip()}"
    return True, f"Task Scheduler: every {m} min (task '{tn}')"


def _schtasks_uninstall(name) -> tuple:
    tn = _job_name(name)
    r = subprocess.run(["schtasks", "/Delete", "/TN", tn, "/F"],
                       capture_output=True, text=True)
    if r.returncode != 0 and "cannot find" not in (r.stderr or "").lower():
        return False, f"schtasks delete failed: {(r.stderr or r.stdout).strip()}"
    return True, "removed"


def _schtasks_is_installed(name, script_path=None) -> bool:
    tn = _job_name(name)
    fields = ["/V", "/FO", "LIST"] if script_path is not None else []
    r = subprocess.run(["schtasks", "/Query", "/TN", tn, *fields],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return False
    if script_path is None:
        return True
    # Same reasoning as the cron version: a task with this NAME existing
    # isn't enough — confirm it actually runs THIS vault's script.
    return str(script_path) in (r.stdout or "")


# ---------------------------------------------------------------- public API


def install(name: str, script_path, every_minutes: int, extra_args=None,
            log_path=None) -> tuple:
    """Install `python3 <script_path> <extra_args>` to run every N minutes.

    Returns (ok: bool, detail: str). Never raises — a scheduling failure is
    reported, not crashed on, because every caller needs to keep going and
    tell the user the rest of the setup status regardless.
    """
    tool, why = available()
    if tool is None:
        return False, f"no scheduler available on this machine — {why}"

    python_exe = sys.executable or "python3"
    script_path = str(Path(script_path).resolve())
    extra_args = extra_args or []

    if tool == "cron":
        parts = [f'"{python_exe}"', f'"{script_path}"'] + [f'"{a}"' for a in extra_args]
        command = " ".join(parts)
        if log_path:
            command += f' >>"{log_path}" 2>&1'
        return _cron_install(name, command, every_minutes)

    if tool == "schtasks":
        return _schtasks_install(name, python_exe, script_path, extra_args,
                                 every_minutes)

    return False, "unreachable"


def uninstall(name: str) -> tuple:
    tool, _ = available()
    if tool == "cron":
        return _cron_uninstall(name)
    if tool == "schtasks":
        return _schtasks_uninstall(name)
    return False, "no scheduler available on this machine"


def is_installed(name: str, script_path=None) -> bool:
    """Is a job with this name scheduled — and, if `script_path` is given,
    does it actually point at THIS script (not a same-named leftover from
    somewhere else)? Always pass `script_path` when you're about to decide
    whether to skip re-installing; omit it only for a general "is anything
    called this scheduled at all" status query.
    """
    if script_path is not None:
        script_path = str(Path(script_path).resolve())
    tool, _ = available()
    if tool == "cron":
        return _cron_is_installed(name, script_path)
    if tool == "schtasks":
        return _schtasks_is_installed(name, script_path)
    return False


JOBS = ("backup-cowork", "vault-snapshot", "changelog-check")


def status_report() -> str:
    tool, why = available()
    lines = [f"scheduler: {tool or 'NONE'} ({why})"]
    if tool:
        for j in JOBS:
            lines.append(f"  {j:<16} {'installed' if is_installed(j) else 'not installed'}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--install", metavar="NAME")
    ap.add_argument("--script", metavar="PATH")
    ap.add_argument("--every-min", type=int, default=60)
    ap.add_argument("--uninstall", metavar="NAME")
    args = ap.parse_args()

    if args.install:
        if not args.script:
            print("--install needs --script <path>", file=sys.stderr)
            return 2
        ok, detail = install(args.install, args.script, args.every_min)
        print(("OK: " if ok else "FAILED: ") + detail)
        return 0 if ok else 1

    if args.uninstall:
        ok, detail = uninstall(args.uninstall)
        print(("OK: " if ok else "FAILED: ") + detail)
        return 0 if ok else 1

    print(status_report())
    return 0


if __name__ == "__main__":
    sys.exit(main())
