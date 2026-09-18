#!/usr/bin/env python3
"""
AIOS/scripts/video.py

Actually watch a video. Prints the real transcript, or fails loudly.

    python3 AIOS/scripts/video.py "https://www.youtube.com/watch?v=XXXX"
    python3 AIOS/scripts/video.py "<url>" --meta-only   # title/channel/length
    python3 AIOS/scripts/video.py --check               # self-test the toolchain
    python3 AIOS/scripts/video.py --list                # what's already cached

WHY THIS EXISTS, in one line: an AI answering off a video's title and
thumbnail instead of its actual content is a real, common failure mode —
this script makes "watch it first" a script that runs, not a promise nobody
checks.

The two failures it fixes
-------------------------

1. **A stale system `yt-dlp` silently fails.** Distro packages lag YouTube's
   changes by months, and YouTube starts returning HTTP 400 to old builds.
   Anything calling bare `yt-dlp` on PATH gets that one. This script never
   trusts PATH — it keeps its own current build under
   ~/.local/share/aios/bin/ and re-downloads it when YouTube starts refusing.

2. **Nothing fetched transcripts at all.** `link.py` pulls title, channel and
   duration, and stops there. So "watch it" had no implementation, and a
   session with no transcript and no error message writes plausible-sounding
   commentary instead of saying "I couldn't."

Which is the design rule here: **an empty transcript is an error, never an
empty string.** This script exits non-zero and says so in words. A session
that can't watch the video has to say so, rather than improvise. See
`Atlas/About Me/Working with AI.md` § "a mechanism, not a promise" — a rule
asking the AI to remember is the weak kind of fix; a script that fails
loudly is the other kind.

Caching
-------

Every transcript is written to `AIOS/history/transcripts/<id>.md` and reused
forever after. Watching a video once makes it readable on every machine, and
readable offline. Notes are free.

No dependencies beyond a `yt-dlp` binary it installs itself. Plain stdlib.
"""

import scriptlog  # noqa: F401 -- logs this run to AIOS/history/scripts/

# aios-run: agent  (every video link seen, no exception -- before answering)

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent.parent
CACHE = VAULT / "AIOS" / "history" / "transcripts"

# Our own yt-dlp, deliberately outside the vault: it's a binary, it's
# machine-specific, and a synced vault folder (Dropbox, iCloud, git) should
# not be shipping a 30 MB executable between machines.
BIN_DIR = Path.home() / ".local" / "share" / "aios" / "bin"
YTDLP = BIN_DIR / "yt-dlp"
YTDLP_URL = ("https://github.com/yt-dlp/yt-dlp/releases/latest/download/"
             "yt-dlp_linux")

SUB_LANGS = "en.*,en"


# ---------------------------------------------------------------- toolchain

def download_ytdlp(reason=""):
    """Fetch a current yt-dlp into BIN_DIR. Returns True on success."""
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    if reason:
        print(f"  video: {reason} -- fetching a current yt-dlp", file=sys.stderr)
    tmp = YTDLP.with_suffix(".part")
    try:
        with urllib.request.urlopen(YTDLP_URL, timeout=120) as r, \
                open(tmp, "wb") as f:
            f.write(r.read())
        tmp.chmod(0o755)
        tmp.replace(YTDLP)
        return True
    except Exception as e:
        if tmp.exists():
            tmp.unlink()
        print(f"  video: !! could not download yt-dlp: {e}", file=sys.stderr)
        return False


def ytdlp_works(path):
    """True if this binary can still talk to YouTube."""
    if not Path(path).exists():
        return False
    try:
        r = subprocess.run([str(path), "--version"],
                           capture_output=True, text=True, timeout=30)
        return r.returncode == 0
    except Exception:
        return False


def ensure_ytdlp(force=False):
    """Return a path to a working yt-dlp, installing one if needed.

    Never falls back to PATH. The whole bug this script exists for is a
    stale system `yt-dlp` being picked up and failing in a way the caller
    doesn't notice.
    """
    if force or not ytdlp_works(YTDLP):
        if not download_ytdlp("no usable yt-dlp" if not force else "refreshing"):
            if ytdlp_works(YTDLP):
                return YTDLP          # old one still runs; try it anyway
            return None
    return YTDLP


# ------------------------------------------------------------------ helpers

# Errors that mean "your yt-dlp is too old", as opposed to "this video is
# gone". Only the first kind is worth re-downloading a 30 MB binary over.
TOOL_FAILURE_SIGNS = (
    "http error 400", "precondition check failed", "unable to download api",
    "requested format is not available", "nsig extraction failed",
    "unable to extract", "player response", "signature extraction",
    "update to the latest version", "only images are available",
)


def looks_like_tool_failure(err: str) -> bool:
    """True if the error smells like a stale binary rather than a dead video."""
    e = (err or "").lower()
    if not e:
        return True          # no error text at all: worth one retry
    if any(s in e for s in ("video is unavailable", "private video",
                            "video unavailable", "has been removed",
                            "members-only", "sign in to confirm your age",
                            "no video formats found", "is not available")):
        return False
    return any(s in e for s in TOOL_FAILURE_SIGNS)


def video_id(url: str) -> str:
    """A stable filename-safe id for the cache."""
    m = re.search(r"(?:v=|youtu\.be/|/shorts/|/embed/)([A-Za-z0-9_-]{6,})", url)
    if m:
        return m.group(1)
    slug = re.sub(r"^https?://", "", url)
    slug = re.sub(r"[^A-Za-z0-9_-]+", "-", slug).strip("-")
    return slug[:80] or "video"


def run_ytdlp(yt, args, timeout=240):
    return subprocess.run([str(yt)] + args, capture_output=True,
                          text=True, timeout=timeout)


def fetch_meta(yt, url):
    """Title, channel, upload date, duration, views. {} if it fails."""
    fmt = "%(title)s\n%(uploader)s\n%(upload_date)s\n%(duration_string)s\n%(view_count)s"
    r = run_ytdlp(yt, ["--skip-download", "--no-warnings", "--print", fmt, url])
    if r.returncode != 0:
        return {}
    lines = [x.strip() for x in r.stdout.strip().splitlines()]
    lines += [""] * (5 - len(lines))
    date = lines[2]
    if len(date) == 8 and date.isdigit():
        date = f"{date[:4]}-{date[4:6]}-{date[6:]}"
    return {"title": lines[0], "channel": lines[1], "uploaded": date,
            "duration": lines[3], "views": lines[4]}


def vtt_to_text(path: Path) -> str:
    """VTT -> flowing plain text.

    Auto-captions repeat each line across cues as the karaoke highlight
    moves, so consecutive duplicates are dropped. Inline <c> timing tags go
    too.
    """
    out = []
    for ln in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "-->" in ln or not ln.strip():
            continue
        if ln.startswith(("WEBVTT", "Kind:", "Language:", "NOTE", "STYLE")):
            continue
        ln = re.sub(r"<[^>]+>", "", ln).strip()
        if ln and (not out or out[-1] != ln):
            out.append(ln)
    return re.sub(r"\s+", " ", " ".join(out)).strip()


def fetch_transcript(yt, url):
    """Download subtitles and return plain text. '' if there are none."""
    with tempfile.TemporaryDirectory() as td:
        r = run_ytdlp(yt, [
            "--skip-download", "--no-warnings",
            "--write-auto-subs", "--write-subs",
            "--sub-langs", SUB_LANGS, "--sub-format", "vtt",
            "-o", os.path.join(td, "sub"), url,
        ])
        vtts = sorted(Path(td).glob("*.vtt"), key=lambda p: p.stat().st_size)
        if not vtts:
            return "", (r.stderr or r.stdout or "").strip()
        # Smallest track is the cleanest: the big ones are word-level
        # auto-caption dumps that dedup down to the same words anyway.
        return vtt_to_text(vtts[0]), ""


# -------------------------------------------------------------------- cache

def cache_path(vid):
    return CACHE / f"{vid}.md"


def read_cache(vid):
    p = cache_path(vid)
    if not p.exists():
        return None
    body = p.read_text(encoding="utf-8", errors="replace")
    parts = body.split("\n---\n", 1)
    return parts[1].strip() if len(parts) == 2 else body.strip()


def write_cache(vid, url, meta, text):
    CACHE.mkdir(parents=True, exist_ok=True)
    head = [f"# {meta.get('title') or url}", "",
            f"- url: {url}"]
    for k in ("channel", "uploaded", "duration", "views"):
        if meta.get(k):
            head.append(f"- {k}: {meta[k]}")
    head.append(f"- words: {len(text.split())}")
    head += ["", "Machine-written by `AIOS/scripts/video.py`. Not a note --",
             "this is the raw transcript, cached so a video is only ever",
             "fetched once. Write what it *means* into a real note.", "",
             "---", ""]
    cache_path(vid).write_text("\n".join(head) + text + "\n", encoding="utf-8")


# --------------------------------------------------------------------- main

def do_check():
    print("video --check")
    yt = ensure_ytdlp()
    if not yt:
        print("  !! no working yt-dlp and none could be downloaded.")
        return 1
    r = run_ytdlp(yt, ["--version"])
    print(f"  yt-dlp .......... {r.stdout.strip()}  ({yt})")
    sysbin = "/usr/bin/yt-dlp"
    if Path(sysbin).exists():
        s = subprocess.run([sysbin, "--version"], capture_output=True, text=True)
        print(f"  system yt-dlp ... {s.stdout.strip()}  (ignored on purpose)")
    print(f"  cache ........... {CACHE}  "
          f"({len(list(CACHE.glob('*.md'))) if CACHE.exists() else 0} cached)")
    print()
    print("  live test against a real video...")
    # "Me at the zoo" -- the first video ever uploaded to YouTube, has English
    # auto-captions, and is the one video on the platform guaranteed never to
    # be deleted. An obvious canary (yt-dlp's own test video) can go dead —
    # that's exactly the silent-canary failure this check exists to catch.
    text, err = fetch_transcript(yt, "https://www.youtube.com/watch?v=jNQXAC9IVRw")
    if not text:
        print(f"  !! FAILED -- no transcript came back. {err[:300]}")
        print("     Videos cannot be watched right now. Say so; don't improvise.")
        return 1
    print(f"  OK -- pulled {len(text.split())} words. Transcripts work.")
    return 0


def do_list():
    if not CACHE.exists() or not any(CACHE.glob("*.md")):
        print("video: nothing cached yet.")
        return 0
    print(f"video: cached transcripts in {CACHE}")
    for p in sorted(CACHE.glob("*.md"), key=lambda x: -x.stat().st_mtime):
        first = p.read_text(encoding="utf-8", errors="replace").splitlines()[0]
        print(f"  {p.stem:<16} {first.lstrip('# ')[:70]}")
    return 0


def main():
    ap = argparse.ArgumentParser(add_help=True, description=(
        "Print a video's real transcript. Exits non-zero if it can't -- "
        "an unavailable transcript is an error, not an empty answer."))
    ap.add_argument("url", nargs="?", help="video URL")
    ap.add_argument("--meta-only", action="store_true",
                    help="title/channel/length, skip the transcript")
    ap.add_argument("--no-cache", action="store_true",
                    help="re-fetch even if it's already cached")
    ap.add_argument("--json", action="store_true", help="machine-readable")
    ap.add_argument("--check", action="store_true",
                    help="self-test the toolchain against a known video")
    ap.add_argument("--list", action="store_true", help="what's cached")
    ap.add_argument("--refresh-tool", action="store_true",
                    help="force-redownload yt-dlp")
    a = ap.parse_args()

    if a.check:
        return do_check()
    if a.list:
        return do_list()
    if a.refresh_tool:
        return 0 if ensure_ytdlp(force=True) else 1
    if not a.url:
        ap.print_help()
        return 2

    vid = video_id(a.url)

    cached = None if a.no_cache else read_cache(vid)
    if cached and not a.meta_only:
        if a.json:
            print(json.dumps({"id": vid, "url": a.url, "cached": True,
                              "transcript": cached}))
        else:
            print(f"# transcript (cached) -- {vid}\n")
            print(cached)
        return 0

    yt = ensure_ytdlp()
    if not yt:
        print("video: !! NO TRANSCRIPT. yt-dlp is unavailable and could not be "
              "installed.\n"
              "       Do NOT describe this video. Say you could not watch it.",
              file=sys.stderr)
        return 1

    meta = fetch_meta(yt, a.url)
    if a.meta_only:
        print(json.dumps(meta) if a.json else "\n".join(
            f"{k}: {v}" for k, v in meta.items() if v))
        return 0 if meta else 1

    text, err = fetch_transcript(yt, a.url)

    # One retry on a fresh binary -- but ONLY when the error looks like the
    # tool being out of date. YouTube breaking an old build is the failure
    # this script was written for, and it's silent.
    #
    # Deliberately NOT retried: "this video is unavailable", private, deleted,
    # age-gated, no captions. Those are facts about the video, and a fresh
    # binary cannot change them. A typo'd video id would otherwise pull a
    # 30 MB download before failing anyway.
    if not text and looks_like_tool_failure(err):
        if ensure_ytdlp(force=True):
            yt = YTDLP
            meta = fetch_meta(yt, a.url) or meta
            text, err = fetch_transcript(yt, a.url)

    if not text:
        print("video: !! NO TRANSCRIPT AVAILABLE for this video.\n"
              "       Do NOT write about what it says. Say you could not\n"
              "       watch it, and why.\n"
              f"       yt-dlp said: {err[:400]}", file=sys.stderr)
        return 1

    write_cache(vid, a.url, meta, text)

    if a.json:
        print(json.dumps({"id": vid, "url": a.url, "cached": False,
                          "meta": meta, "transcript": text}))
        return 0

    print(f"# {meta.get('title') or a.url}")
    bits = [meta.get(k) for k in ("channel", "uploaded", "duration") if meta.get(k)]
    if meta.get("views"):
        bits.append(f"{int(meta['views']):,} views")
    if bits:
        print(" · ".join(bits))
    print(f"\n({len(text.split())} words, cached to "
          f"AIOS/history/transcripts/{vid}.md)\n")
    print(text)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
