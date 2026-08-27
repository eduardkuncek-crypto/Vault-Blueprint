#!/usr/bin/env python3
"""
chronicle.py — build AIOS/history/chat-history/curated/YYYY-MM-DD-<topic>.md
from an already backed-up chat, instead of retyping the whole conversation
by hand.

Why this exists: `backup-cowork.py` already saves every Cowork chat as
readable Markdown into `AIOS/history/chat-history/cowork/`. Retyping the
conversation a second time duplicates content that already exists. This
script finds the right backed-up chat and copies it, with a
decisions/action-items/open-questions header on top.

Usage:
    python3 AIOS/scripts/chronicle.py --list
        List backed-up chats, newest first, so you can see what's available.

    python3 AIOS/scripts/chronicle.py "<topic>" --find "<keyword>"
        Find the newest backed-up chat whose filename or content matches
        <keyword> (case-insensitive), and write
        AIOS/history/chat-history/curated/YYYY-MM-DD-<topic-slug>.md from it.

    python3 AIOS/scripts/chronicle.py "<topic>" --find "<keyword>" \\
        --decisions "Decided X; decided Y" \\
        --actions "Buy Z; email someone" \\
        --open "Still unclear if W"
        Same, with the header sections filled in instead of left as
        placeholders. Each is split on ';' into separate bullet lines.

    python3 AIOS/scripts/chronicle.py "<topic>" --latest
        Skip the keyword search, just use the single most recently
        backed-up chat.

Honest limit: this can only chronicle a chat that has ALREADY been backed up.
`backup-cowork.py` has to run on your own machine, not from inside a cloud
Cowork session — a cloud session can't reach your local Claude app's files.
So THIS session's transcript is not available to chronicle until you run the
backup on your own machine. If you ask for the chat happening right now,
this script says so rather than silently grabbing an older one.

No dependencies. Plain stdlib.
"""
import argparse
import os
import re
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
VAULT = os.path.abspath(os.path.join(HERE, "..", ".."))
COWORK_DIR = os.path.join(VAULT, "AIOS", "history", "chat-history", "cowork")
OUT_DIR = os.path.join(VAULT, "AIOS", "history", "chat-history", "curated")


def find_transcripts():
    """Every backed-up chat .md file."""
    out = []
    if not os.path.isdir(COWORK_DIR):
        return out
    for fn in os.listdir(COWORK_DIR):
        if fn.endswith(".md") and fn.lower() not in ("index.md", "cowork chats.md"):
            p = os.path.join(COWORK_DIR, fn)
            out.append((os.path.getmtime(p), p))
    out.sort(reverse=True)
    return out


def slugify(topic):
    s = re.sub(r"[^a-zA-Z0-9]+", "-", topic.strip().lower()).strip("-")
    return s or "chat"


def bullets(raw):
    if not raw:
        return "_(none noted)_"
    parts = [p.strip() for p in raw.split(";") if p.strip()]
    return "\n".join(f"- {p}" for p in parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("topic", nargs="?", help="short topic for the filename/title")
    ap.add_argument("--list", action="store_true", help="list backed-up chats and exit")
    ap.add_argument("--find", metavar="KEYWORD", help="match chat filename or content")
    ap.add_argument("--latest", action="store_true", help="use the most recent chat, no keyword match")
    ap.add_argument("--decisions", default="", help="';'-separated decisions made")
    ap.add_argument("--actions", default="", help="';'-separated action items")
    ap.add_argument("--open", dest="open_qs", default="", help="';'-separated open questions")
    args = ap.parse_args()

    transcripts = find_transcripts()

    if args.list:
        if not transcripts:
            print("chronicle: no backed-up chats found under AIOS/history/chat-history/cowork/. "
                  "backup-cowork.py hasn't run yet on this machine.")
            return 1
        for mtime, p in transcripts[:30]:
            when = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
            print(f"{when}  {os.path.relpath(p, VAULT)}")
        return 0

    if not args.topic:
        ap.error("topic is required unless --list is given")

    if not transcripts:
        print("chronicle: no backed-up chats found under AIOS/history/chat-history/cowork/. "
              "backup-cowork.py runs on your own machine, not inside a cloud "
              "Cowork session. If this is about the chat happening right "
              "now, it isn't backed up yet; run backup-cowork.py by hand "
              "on your machine first.", file=sys.stderr)
        return 1

    match = None
    if args.latest and not args.find:
        match = transcripts[0]
    elif args.find:
        kw = args.find.lower()
        for mtime, p in transcripts:
            if kw in os.path.basename(p).lower():
                match = (mtime, p)
                break
        if match is None:
            for mtime, p in transcripts:
                try:
                    text = open(p, encoding="utf-8", errors="replace").read()
                except OSError:
                    continue
                if kw in text.lower():
                    match = (mtime, p)
                    break
    else:
        ap.error("give --find <keyword> or --latest so the right chat gets picked")

    if match is None:
        print(f"chronicle: no backed-up chat matched '{args.find}'. "
              f"Run with --list to see what's actually available.", file=sys.stderr)
        return 1

    mtime, src_path = match
    transcript = open(src_path, encoding="utf-8", errors="replace").read()

    today = datetime.now().strftime("%Y-%m-%d")
    slug = slugify(args.topic)
    out_name = f"{today}-{slug}.md"
    out_path = os.path.join(OUT_DIR, out_name)

    if os.path.exists(out_path):
        print(f"chronicle: {os.path.relpath(out_path, VAULT)} already exists — "
              f"pick a different topic or delete it first (never overwritten "
              f"automatically).", file=sys.stderr)
        return 1

    lines = []
    lines.append("---")
    lines.append(f"title: {args.topic}")
    lines.append("tags:")
    lines.append("  - chronicle")
    lines.append("  - chat-log")
    lines.append(f"date: {today}")
    lines.append(f"source: {os.path.relpath(src_path, VAULT)}")
    lines.append("---")
    lines.append("")
    lines.append(f"# {args.topic}")
    lines.append("")
    lines.append("## Decisions made")
    lines.append("")
    lines.append(bullets(args.decisions))
    lines.append("")
    lines.append("## Action items")
    lines.append("")
    lines.append(bullets(args.actions))
    lines.append("")
    lines.append("## Open questions")
    lines.append("")
    lines.append(bullets(args.open_qs))
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(transcript.rstrip())
    lines.append("")

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"wrote {os.path.relpath(out_path, VAULT)}")
    print(f"  source: {os.path.relpath(src_path, VAULT)}")
    if not args.decisions and not args.actions and not args.open_qs:
        print("  header sections left as placeholders — fill them in, or "
              "re-run with --decisions/--actions/--open")
    return 0


if __name__ == "__main__":
    sys.exit(main())
