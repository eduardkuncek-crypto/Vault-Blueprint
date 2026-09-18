#!/usr/bin/env python3
"""
AIOS/scripts/hook-video.py

UserPromptSubmit hook. You paste a video link -> the transcript is already
in context before the model writes a single word.

Install (Claude Code / Cowork):

    python3 AIOS/scripts/hook-video.py --install-hook

Wires itself into ~/.claude/settings.json and ~/.config/Claude/settings.json
as:

    "hooks": { "UserPromptSubmit": [ { "hooks": [
        { "type": "command",
          "command": "python3 /path/to/your-vault/AIOS/scripts/hook-video.py" } ] } ] }

WHY THIS EXISTS, in one line: `video.py` and the `link` routine both work,
but both depend on the model *choosing* to run them — and a model that
already has a plausible-sounding guess doesn't always choose to.

This is the layer under that. The harness executes it on every prompt
submitted. There is no decision point, so there is nothing to skip. That is
the whole difference between this file and a rule in `me.md`, and it's the
pattern `Atlas/About Me/Working with AI.md` calls "a mechanism, not a
promise."

Reads the hook payload on stdin, writes JSON on stdout. Silent and instant
when there's no video link, which is almost every prompt.

Failure is loud, same contract as video.py: if a transcript can't be had, it
says so in the injected context and tells the model not to invent one. It
never stays quiet about a video it couldn't open.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
VIDEO_PY = SCRIPTS / "video.py"

URL_RE = re.compile(
    r"https?://(?:www\.|m\.)?(?:youtube\.com/(?:watch\?\S*?v=|shorts/|live/|embed/)"
    r"|youtu\.be/)([A-Za-z0-9_-]{6,})", re.I)

MAX_WORDS = 12000       # a ~90 min video; longer gets truncated with a pointer
MAX_VIDEOS = 3          # more than one link pasted at once


# Every settings file a Claude client on this machine might read. Both get the
# hook: they're separate stores (~/.claude is the CLI, ~/.config/Claude is the
# desktop app), and which one is live depends on which app is open. Installing
# to both is cheap; guessing wrong means the hook silently never fires.
SETTINGS_CANDIDATES = [
    Path.home() / ".claude" / "settings.json",
    Path.home() / ".config" / "Claude" / "settings.json",
]


def install_hook(quiet=False):
    """Wire this script into every Claude settings file on this machine.

    Merges. Never clobbers existing hooks or any other setting. Safe to run
    twice -- it replaces only its own entry.

    This is what makes a new computer work: the path below is computed from
    where this file actually is, so it's correct on any machine and under any
    username without editing anything.
    """
    cmd = f"{sys.executable} {Path(__file__).resolve()}"
    entry = {"type": "command", "command": cmd, "timeout": 300,
             "statusMessage": "Watching the video..."}
    done = []
    for path in SETTINGS_CANDIDATES:
        if not path.parent.exists():
            continue                      # that client isn't installed here
        try:
            data = json.loads(path.read_text()) if path.exists() else {}
            if not isinstance(data, dict):
                data = {}
        except Exception:
            print(f"  !! {path} is not valid JSON -- leaving it alone.")
            continue

        hooks = data.setdefault("hooks", {})
        groups = hooks.setdefault("UserPromptSubmit", [])
        # Drop any previous copy of *this* script, keep everything else.
        for g in groups:
            g["hooks"] = [h for h in g.get("hooks", [])
                          if "hook-video.py" not in str(h.get("command", ""))]
        groups[:] = [g for g in groups if g.get("hooks")]
        groups.append({"hooks": [entry]})

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + "\n")
        done.append(path)

    if not quiet:
        print("hook-video --install-hook")
        if done:
            for p in done:
                print(f"  installed -> {p}")
            print(f"  command ... {cmd}")
            print()
            print("  Restart the Claude app (or open /hooks once) so it")
            print("  re-reads settings. Then paste any YouTube link.")
        else:
            print("  !! no Claude settings directory found on this machine.")
            return 1
    return 0


def out(obj):
    print(json.dumps(obj))
    sys.exit(0)


def nothing():
    # No video in this prompt: emit nothing and get out of the way.
    sys.exit(0)


def main():
    if "--install-hook" in sys.argv:
        sys.exit(install_hook())

    try:
        payload = json.load(sys.stdin)
    except Exception:
        nothing()

    prompt = payload.get("prompt") or ""
    if not isinstance(prompt, str) or "youtu" not in prompt.lower():
        nothing()

    urls, seen = [], set()
    for m in URL_RE.finditer(prompt):
        vid = m.group(1)
        if vid not in seen:
            seen.add(vid)
            urls.append(m.group(0))
    if not urls:
        nothing()

    blocks, failed = [], []
    for url in urls[:MAX_VIDEOS]:
        try:
            r = subprocess.run(
                [sys.executable, str(VIDEO_PY), url],
                capture_output=True, text=True, timeout=300)
        except Exception as e:
            failed.append((url, str(e)))
            continue
        if r.returncode != 0 or not r.stdout.strip():
            failed.append((url, (r.stderr or "").strip()[:300]))
            continue

        text = r.stdout.strip()
        words = text.split()
        if len(words) > MAX_WORDS:
            text = " ".join(words[:MAX_WORDS]) + (
                f"\n\n[... truncated at {MAX_WORDS} words. Full text: "
                f"AIOS/history/transcripts/ ...]")
        blocks.append(text)

    if not blocks and not failed:
        nothing()

    parts = []
    if blocks:
        parts.append(
            "A video link was pasted. It has already been watched for you — "
            "the real transcript is below, pulled by `AIOS/scripts/video.py` "
            "and cached in `AIOS/history/transcripts/`.\n\n"
            "Use THIS, not the title, not the thumbnail, not what this channel "
            "usually argues.\n\n"
            + "\n\n---\n\n".join(blocks))

    for url, err in failed:
        parts.append(
            f"!! COULD NOT WATCH {url}\n"
            f"   {err}\n"
            "   Do NOT describe this video or guess what's in it. Say plainly "
            "that you couldn't watch it, and why. That is a complete and "
            "acceptable answer.")

    out({
        "suppressOutput": True,
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": "\n\n".join(parts),
        },
    })


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # A broken hook must never block a message from being sent.
        sys.exit(0)
