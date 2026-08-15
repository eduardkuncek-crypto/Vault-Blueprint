#!/usr/bin/env python3
"""
backup-cowork — copy your Claude/Cowork chat history into this vault so it
survives a reinstall, a dead disk, or Claude clearing its own cache.

RUN THIS ON YOUR OWN COMPUTER, in a real terminal — not by asking an AI to run
it inside a cloud/sandboxed session. A cloud session cannot see your local
Claude app's files; it isn't a limitation of this script, it's how sandboxing
works everywhere. See "Where this looks for your chats" below for how to tell
the difference.

    python3 AIOS/scripts/backup-cowork.py
    python3 AIOS/scripts/backup-cowork.py --install-schedule --every-min 60
    python3 AIOS/scripts/backup-cowork.py --uninstall-schedule

It only ever READS from your local Claude app folder and WRITES inside this
vault, under AIOS/history/chat-history/cowork/. It never deletes anything and
is safe to run as often as you like — unchanged files are skipped.

What it saves
--------------
  AIOS/history/chat-history/cowork/        every conversation, as readable Markdown
  AIOS/history/chat-history/cowork-raw/    the same conversations exactly as Claude stored them (.jsonl)

Why both: the raw .jsonl is the real backup and cannot lose anything. The
Markdown is what you'd actually open and read. If the Markdown conversion
ever breaks because Claude changes its file format, the raw copies are still
complete and nothing is lost.

Where this looks for your chats
--------------------------------
Claude's desktop app stores local session data in a different place on each
OS. This script tries every known location and uses whichever one actually
exists on this machine:

  Linux    ~/.config/Claude/local-agent-mode-sessions
  macOS    ~/Library/Application Support/Claude/local-agent-mode-sessions
  Windows  %APPDATA%\\Claude\\local-agent-mode-sessions
           %LOCALAPPDATA%\\Claude\\local-agent-mode-sessions

If none of those exist, this prints exactly which paths it checked so you (or
whoever's helping you) can find the real one and add it to CANDIDATE_PATHS
below — Claude's storage location has moved before and will probably move
again.

No dependencies. Plain stdlib.
"""
import json
import os
import platform
import shutil
import sys
from datetime import datetime
from pathlib import Path

HOME = Path.home()


def candidate_paths():
    """Every place Claude's local session data might live, most likely first."""
    system = platform.system()
    out = []
    if system == "Darwin":
        out.append(HOME / "Library" / "Application Support" / "Claude" /
                   "local-agent-mode-sessions")
    elif system == "Windows":
        appdata = os.environ.get("APPDATA")
        localappdata = os.environ.get("LOCALAPPDATA")
        if appdata:
            out.append(Path(appdata) / "Claude" / "local-agent-mode-sessions")
        if localappdata:
            out.append(Path(localappdata) / "Claude" / "local-agent-mode-sessions")
    else:  # Linux and anything else POSIX
        out.append(HOME / ".config" / "Claude" / "local-agent-mode-sessions")
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        out.append(Path(xdg) / "Claude" / "local-agent-mode-sessions")
    return out


# This script lives at <vault>/AIOS/scripts/backup-cowork.py, so the vault is
# two levels up — found this way, not hardcoded, so renaming the vault folder
# never breaks it.
VAULT = Path(__file__).resolve().parent.parent.parent
DEST_RAW = VAULT / "AIOS" / "history" / "chat-history" / "cowork-raw"
DEST_MD = VAULT / "AIOS" / "history" / "chat-history" / "cowork"

stats = {"raw": 0, "raw_skipped": 0, "md": 0, "md_skipped": 0, "md_failed": 0,
         "bytes": 0}


def find_source():
    for p in candidate_paths():
        if p.is_dir():
            return p
    return None


def copy_if_newer(src: Path, dst: Path) -> bool:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        s, d = src.stat(), dst.stat()
        if s.st_size == d.st_size and s.st_mtime <= d.st_mtime:
            return False
    shutil.copy2(src, dst)
    stats["bytes"] += src.stat().st_size
    return True


def text_of(content) -> str:
    """Pull readable text out of a message body, whatever shape it is."""
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    out = []
    for block in content:
        if not isinstance(block, dict):
            out.append(str(block))
            continue
        t = block.get("type")
        if t == "text":
            out.append(block.get("text", ""))
        elif t == "thinking":
            continue
        elif t == "tool_use":
            out.append(f"*[used tool: {block.get('name', 'unknown')}]*")
        elif t == "tool_result":
            out.append("*[tool result]*")
    return "\n\n".join(x for x in out if x)


def jsonl_to_markdown(path: Path):
    """Best-effort conversion. Returns (markdown, n_messages) or (None, 0)."""
    rows = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    if not rows:
        return None, 0

    first_ts = next((r.get("timestamp") for r in rows if r.get("timestamp")), "")
    date = (first_ts or "")[:10] or "unknown-date"

    title = "Cowork chat"
    for r in rows:
        if r.get("type") == "user":
            msg = r.get("message") or {}
            txt = text_of(msg.get("content", "")).strip()
            if txt and not txt.startswith("<"):
                title = " ".join(txt.split())[:70]
                break

    out = ["---",
           f'title: "{title.replace(chr(34), chr(39))}"',
           f"date: {date}",
           "tags:",
           "  - chat-log",
           f"source: {path.name}",
           "---",
           "",
           f"# {title}",
           "",
           "> [!quote] Automatic chat transcript — not a note",
           "> Written by `AIOS/scripts/backup-cowork.py`, overwritten on every"
           " run. Don't edit it. If something here matters, put it in the"
           " relevant note instead — that's the rule in `AIOS/me.md`.",
           ">",
           "> Deliberately **no wikilinks** in generated transcripts — dozens"
           " of chat files each linking to `me.md` would bury that note's"
           " real backlinks under machine-written noise.",
           "",
           f"*Backed up {datetime.now().strftime('%Y-%m-%d %H:%M')} from "
           f"`{path.name}`*",
           ""]

    n = 0
    for r in rows:
        role = r.get("type")
        if role not in ("user", "assistant"):
            continue
        msg = r.get("message") or {}
        body = text_of(msg.get("content", "")).strip()
        if not body:
            continue
        if role == "user" and body == "*[tool result]*":
            continue
        ts = (r.get("timestamp") or "")[11:16]
        who = "**You**" if role == "user" else "**Claude**"
        out.append(f"### {who}" + (f" · {ts}" if ts else ""))
        out.append("")
        out.append(body)
        out.append("")
        n += 1

    return "\n".join(out), n


def backup_chats(src: Path):
    for dp, dns, fns in os.walk(src):
        dns[:] = [d for d in dns if d not in ("node_modules", "backups")]
        for fn in fns:
            s = Path(dp) / fn
            rel = s.relative_to(src)

            if fn.endswith(".jsonl") and "projects" in s.parts:
                if copy_if_newer(s, DEST_RAW / rel):
                    stats["raw"] += 1
                else:
                    stats["raw_skipped"] += 1
                try:
                    md, n = jsonl_to_markdown(s)
                    if md and n:
                        stem = fn[:-6] if fn.endswith(".jsonl") else fn
                        name = f"{md.split('date: ')[1][:10]}-{stem[:8]}.md"
                        p = DEST_MD / name
                        p.parent.mkdir(parents=True, exist_ok=True)
                        old = p.read_text(encoding="utf-8") if p.exists() else ""

                        def strip_ts(t):
                            return "\n".join(
                                ln for ln in t.splitlines()
                                if not ln.startswith("*Backed up "))
                        if strip_ts(old) != strip_ts(md):
                            p.write_text(md, encoding="utf-8")
                            stats["md"] += 1
                        else:
                            stats["md_skipped"] += 1
                except Exception as e:
                    stats["md_failed"] += 1
                    print(f"  .. couldn't convert {fn}: {e}")


def write_history_index():
    files = sorted((f.name for f in DEST_MD.glob("*.md")
                    if f.name != "Cowork chats.md"), reverse=True)

    (DEST_MD / "Cowork chats.base").write_text(
        'filters:\n  and:\n'
        '    - file.inFolder("AIOS/history/chat-history/cowork")\n'
        '    - file.hasTag("chat-log")\n'
        'properties:\n'
        '  file.name:\n    displayName: Chat\n'
        '  title:\n    displayName: Opened with\n'
        '  date:\n    displayName: Date\n'
        'views:\n'
        '  - type: table\n    name: All chats\n'
        '    order:\n      - title\n      - date\n      - file.mtime\n'
        '  - type: table\n    name: This month\n'
        '    filters:\n      and:\n'
        '        - \'file.mtime > now() - "30d"\'\n'
        '    order:\n      - title\n      - date\n', encoding="utf-8")

    (DEST_MD / "Cowork chats.md").write_text(
        "---\ntitle: Cowork chats\ntags:\n  - index\n---\n\n"
        "# Cowork chats\n\n"
        f"**{len(files)} conversations**, updated "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M')}.\n\n"
        "> [!warning] This whole folder is generated. Don't edit anything in it.\n"
        "> Written by `AIOS/scripts/backup-cowork.py`. Every file here is\n"
        "> overwritten on each run.\n>\n"
        "> These are **chat logs, not notes**. `AIOS/me.md` is explicit: save\n"
        "> facts, not chat logs. They live here so nothing is lost and so you\n"
        "> can search old conversations — **not** so decisions can live here.\n"
        "> A decision that only exists in this folder is a decision the next\n"
        "> session will re-argue. Put it in the relevant note.\n\n"
        "![[Cowork chats.base]]\n\n"
        "## Searching these\n\n"
        "In Obsidian, restrict a search to just chats with:\n\n"
        "```\ntag:#chat-log \"the thing you're looking for\"\n```\n\n"
        "Or exclude them from a normal search with `-tag:#chat-log`.\n\n"
        "## Related\n\n- [[Home]]\n", encoding="utf-8")


def main() -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import scheduler  # noqa: E402

    if "--install-schedule" in sys.argv or "--install-cron" in sys.argv:
        every = 60
        if "--every-min" in sys.argv:
            every = int(sys.argv[sys.argv.index("--every-min") + 1])
        ok, detail = scheduler.install("backup-cowork", Path(__file__),
                                       every_minutes=every)
        print(("Installed. " if ok else "Could NOT install automatically. ")
              + detail)
        if not ok:
            print("  You'll need to run this script by hand from time to "
                  "time instead, or set it up in your OS's own scheduler.")
            return 1
        print()
        print("Running it once now so you don't wait for the first scheduled run:")
        print()

    if "--uninstall-schedule" in sys.argv or "--uninstall-cron" in sys.argv:
        ok, detail = scheduler.uninstall("backup-cowork")
        print(("Removed. " if ok else "Could not remove: ") + detail)
        return 0 if ok else 1

    print("backup-cowork")
    if not (VAULT / "AIOS").is_dir():
        print(f"  !! {VAULT} doesn't look like the vault (no AIOS/ folder).")
        print("     Run this script from where it lives inside the vault.")
        return 1

    src = find_source()
    if src is None:
        print("  !! Couldn't find your Claude app's chat folder. Checked:")
        for p in candidate_paths():
            print(f"       {p}  {'(exists)' if p.exists() else '(not found)'}")
        print()
        print("  If Claude is installed somewhere unusual on this machine,")
        print("  find the real folder and edit candidate_paths() in this script.")
        print("  If this is a cloud/sandboxed session rather than your own")
        print("  computer, that's expected — this has to run on the machine")
        print("  where the Claude app itself is installed.")
        return 1

    print(f"  from: {src}")
    print(f"  to:   {DEST_MD.relative_to(VAULT)}  (readable)")
    print(f"        {DEST_RAW.relative_to(VAULT)}  (raw, exact)")
    print()

    DEST_RAW.mkdir(parents=True, exist_ok=True)
    DEST_MD.mkdir(parents=True, exist_ok=True)
    backup_chats(src)
    write_history_index()

    print("  markdown transcripts . %d new/updated  (%d unchanged, %d failed)"
          % (stats["md"], stats["md_skipped"], stats["md_failed"]))
    print("  raw files ............ %d new/updated  (%d unchanged)"
          % (stats["raw"], stats["raw_skipped"]))
    print("  new data ............. %.2f MB" % (stats["bytes"] / 1048576))
    print()
    total = stats["raw"] + stats["raw_skipped"]
    if total == 0:
        print("  NOTHING FOUND at that path. It exists but is empty — either")
        print("  you haven't had a Cowork/local-agent-mode conversation on")
        print("  this machine yet, or Claude stores it somewhere this script")
        print("  doesn't check yet.")
        return 1
    print(f"  Done. {total} conversation file(s) tracked in total.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
