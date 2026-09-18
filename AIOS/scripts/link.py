#!/usr/bin/env python3
"""
AIOS/scripts/link.py

Save a link. Every link you send gets its own note in `Atlas/Links/`.

    python3 AIOS/scripts/link.py "https://example.com/thing"
    python3 AIOS/scripts/link.py "https://a.com" "https://b.com" --why "for the server build"
    python3 AIOS/scripts/link.py --from-text "check these out https://a.com and https://b.com"

    python3 AIOS/scripts/link.py --list            # newest 20
    python3 AIOS/scripts/link.py --find "arch"     # search title, url, why, tags
    python3 AIOS/scripts/link.py --set "arch" read # flip a link's status
    python3 AIOS/scripts/link.py --check           # re-test every link, mark dead ones
    python3 AIOS/scripts/link.py --rebuild         # regenerate the index from the notes

One note per link, per the vault's one-subject-one-note rule — the URL, the
site, what the page is, and an empty `## My notes` section for whatever you
want to add later. `Atlas/Links/Links.md` is the index, and it is
**generated from the notes**, so the notes are the truth and the index can
never disagree with them.

The script goes and fetches each page, so a note says what the link actually
*is* — real title, site name, the page's own description — instead of a bare
URL nobody can identify six months later.

WHY THIS EXISTS, in one line: a URL pasted into a chat is gone the moment the
chat scrolls, and "that thing you sent me" is not a searchable string.

Design notes:

  * **The URL is the identity, the filename is just a label.** Tracking junk
    (`utm_*`, `fbclid`, `si`, ...) is stripped before saving, so the same link
    shared from Twitter and from a phone is one note, not two. Re-saving a
    link updates the note it already has.
  * **Your half of a note is never overwritten.** Only the frontmatter and the
    block between the `GENERATED` markers get rewritten. `## My notes` and
    anything you add below it are left exactly alone, on every update, on
    every `--check`, forever.
  * **It never loses a link to a failed fetch.** No network, 403, dead
    domain — the note is still written, with the path or domain as the title
    and the failure recorded. `--check` fills the real title in later.
  * **YouTube gets special handling** because the plain page is a JS shell
    with no useful title for a human. If `yt-dlp` is on PATH it's used for
    the real title, channel and duration. If it isn't, the normal path still
    works.
  * **It logs itself.** `logchange.py` runs at the end, so a saved link gets
    its receipt in today's `## Changes` without anyone remembering to.

No dependencies. Plain stdlib.
"""

import scriptlog  # noqa: F401 -- logs this run to AIOS/history/scripts/

# aios-run: agent  (every single link sent, no exception)

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from html import unescape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P  # noqa: E402

LINKS_DIR = P.VAULT / "Atlas" / "Links"
INDEX = P.VAULT / "Atlas" / "Links" / "Links.md"
BASE = P.VAULT / "Atlas" / "Links" / "Links.base"

STATUSES = ("unread", "read", "useful", "dead")
COLUMNS = ["Link", "What it is", "Site", "Saved", "Status"]

NOTE_BEGIN = "<!-- BEGIN GENERATED: link -->"
NOTE_END = "<!-- END GENERATED: link -->"
INDEX_BEGIN = "<!-- BEGIN GENERATED: index -->"
INDEX_END = "<!-- END GENERATED: index -->"
MY_NOTES = "## My notes"

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
TIMEOUT = 12
MAX_BYTES = 400_000  # enough for any <head>, never a whole video

# Query parameters that identify the sharer, not the thing being shared.
JUNK_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "utm_id", "utm_name", "fbclid", "gclid", "gclsrc", "dclid", "msclkid",
    "igshid", "igsh", "mc_cid", "mc_eid", "ref_src", "ref_url", "ref",
    "source", "spm", "si", "pp", "feature", "ab_channel", "app",
    "share_id", "share", "__twitter_impression", "s", "cmpid", "ncid",
    "_branch_match_id", "yclid", "at_medium", "at_campaign",
}
# ...except on these hosts, where a stripped param breaks the link.
JUNK_EXEMPT_HOSTS = {"google.com", "www.google.com", "duckduckgo.com",
                     "github.com", "stackoverflow.com", "reddit.com",
                     "www.reddit.com", "amazon.de", "amazon.com"}

URL_RE = re.compile(r"""(?xi)
    \b (?: https?://  |  www\. )
    [^\s<>"'`]+
""")

# Characters a filename can't hold on Linux/Windows/Dropbox, plus the two
# that would break a wikilink pointing at the note.
BAD_FILENAME = re.compile(r"""[/\\:*?"<>|\[\]#^]""")


def fail(msg, code=1):
    print(f"link: {msg}", file=sys.stderr)
    sys.exit(code)


def write_atomic(path: Path, text: str):
    """Write via a temp file in the same directory, then replace. A
    half-written note on a crash would be worse than a lost link."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


# ------------------------------------------------------------------ url shape

def normalize(raw: str) -> str:
    """One canonical spelling per link, so the same thing shared two ways
    doesn't become two notes."""
    url = raw.strip().strip("<>").rstrip(".,;:!?)]}'\"")
    if not url:
        return ""
    # A non-web scheme is not a link to save. Catch it before the bare-domain
    # branch below, or `mailto:a@b.com` becomes `https://mailto:a@b.com`.
    # The (?!\d) keeps `example.com:8080/x` out of this — that's a port, not
    # a scheme, and it still wants https:// in front.
    scheme = re.match(r"^([a-zA-Z][a-zA-Z0-9+.\-]*):(?!\d)", url)
    if scheme and scheme.group(1).lower() not in ("http", "https"):
        return ""
    if "://" not in url:
        url = "https://" + url

    try:
        u = urllib.parse.urlsplit(url)
    except ValueError:
        return ""
    if u.scheme not in ("http", "https") or not u.netloc:
        return ""

    host = u.netloc.lower()
    if host.startswith("m.") and host.count(".") >= 2:
        host = host[2:]                      # m.youtube.com -> youtube.com
    if host.endswith(":80"):
        host = host[:-3]
    if host.endswith(":443"):
        host = host[:-4]

    # youtu.be/ID -> youtube.com/watch?v=ID, so both spellings are one note
    query = urllib.parse.parse_qsl(u.query, keep_blank_values=False)
    path = u.path
    if host in ("youtu.be", "www.youtu.be"):
        vid = path.strip("/").split("/")[0]
        if vid:
            host, path = "www.youtube.com", "/watch"
            query = [("v", vid)] + [(k, v) for k, v in query if k == "t"]
    elif host == "youtube.com":
        host = "www.youtube.com"

    if host not in JUNK_EXEMPT_HOSTS:
        query = [(k, v) for k, v in query if k.lower() not in JUNK_PARAMS]

    if path.endswith("/") and path != "/":
        path = path.rstrip("/")

    return urllib.parse.urlunsplit(
        (u.scheme, host, path, urllib.parse.urlencode(query), ""))


def domain(url: str) -> str:
    host = urllib.parse.urlsplit(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def extract_urls(text: str) -> list:
    """Every URL in a blob of pasted text, deduped, in the order they appear."""
    out, seen = [], set()
    for m in URL_RE.finditer(text or ""):
        n = normalize(m.group(0))
        if n and n not in seen:
            seen.add(n)
            out.append(n)
    return out


# --------------------------------------------------------------- page fetch

def clean(s: str) -> str:
    """Single line, no control characters. Safe anywhere."""
    return re.sub(r"\s+", " ", (s or "")).strip()


def cell(s: str) -> str:
    """Single line, safe inside a Markdown table cell."""
    return clean(s).replace("|", "\\|")


def _decode(body: bytes, ctype: str) -> str:
    enc = None
    m = re.search(r"charset=([\w\-]+)", ctype or "", re.I)
    if m:
        enc = m.group(1)
    if not enc:
        m = re.search(rb'charset=["\']?([\w\-]+)', body[:4000], re.I)
        if m:
            enc = m.group(1).decode("ascii", "ignore")
    try:
        return body.decode(enc or "utf-8", errors="replace")
    except LookupError:
        return body.decode("utf-8", errors="replace")


def _meta(html: str, *keys) -> str:
    """First matching <meta property/name=...> content, in the order given."""
    for key in keys:
        pat = (r"""<meta[^>]+(?:property|name)\s*=\s*["']%s["'][^>]*"""
               r"""content\s*=\s*["'](.*?)["']""" % re.escape(key))
        m = re.search(pat, html, re.I | re.S)
        if not m:  # attribute order is not guaranteed — try content first
            pat = (r"""<meta[^>]+content\s*=\s*["'](.*?)["'][^>]*"""
                   r"""(?:property|name)\s*=\s*["']%s["']""" % re.escape(key))
            m = re.search(pat, html, re.I | re.S)
        if m and m.group(1).strip():
            return clean(unescape(m.group(1)))
    return ""


def _ytdlp() -> str:
    """Path to a yt-dlp that actually works, or ''.

    Deliberately NOT `shutil.which("yt-dlp")`. A distro-packaged build can be
    on PATH and still fail against YouTube, which is the worst case — a tool
    that exists and returns an error the caller can silently treat as "this
    video has no data". `video.py` owns a current build and self-heals; ask
    it instead.
    """
    try:
        import video
        yt = video.ensure_ytdlp()
        return str(yt) if yt else ""
    except Exception:
        return shutil.which("yt-dlp") or ""


VIDEO_HOSTS = ("youtube.com", "youtu.be")


def pull_transcript(url: str):
    """For a video link, cache its transcript. Returns (path, words) or None.

    Saving a video link and *watching* it used to be two separate acts, and
    the second one had no implementation — so a session could write about a
    video from its title alone. Now the act that already happens
    unconditionally (saving the link) also puts the words on disk. Nobody has
    to remember anything.
    """
    if domain(url) not in VIDEO_HOSTS:
        return None
    try:
        import video
        yt = video.ensure_ytdlp()
        if not yt:
            return ("", 0)
        vid = video.video_id(url)
        cached = video.read_cache(vid)
        if cached:
            return (video.cache_path(vid), len(cached.split()))
        text, _err = video.fetch_transcript(yt, url)
        if not text:
            return ("", 0)
        video.write_cache(vid, url, video.fetch_meta(yt, url) or {}, text)
        return (video.cache_path(vid), len(text.split()))
    except Exception:
        return ("", 0)


def youtube_meta(url: str) -> dict:
    """Real title/channel/duration via yt-dlp, if it's installed.

    The default player client 400s on some videos, so ask for the mobile-web
    one, which has been the reliable fallback."""
    yt_bin = _ytdlp()
    if not yt_bin:
        return {}
    try:
        r = subprocess.run(
            [yt_bin, "--extractor-args", "youtube:player_client=mweb",
             "--ignore-no-formats-error", "--skip-download", "--no-warnings",
             "--print", "%(title)s", "--print", "%(uploader)s",
             "--print", "%(duration_string)s", url],
            capture_output=True, text=True, timeout=60, check=False)
    except (subprocess.TimeoutExpired, OSError):
        return {}
    lines = [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]
    if r.returncode != 0 or not lines:
        return {}
    out = {"title": clean(lines[0]), "site": "YouTube"}
    bits = [ln for ln in lines[1:3] if ln not in ("NA", "None")]
    out["desc"] = clean(" · ".join(bits))
    return out


def fetch_meta(url: str) -> dict:
    """What the page says it is. Never raises — a failure is a result."""
    host = domain(url)
    if host in ("youtube.com", "youtu.be"):
        yt = youtube_meta(url)
        if yt.get("title"):
            return yt

    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Language": "en,de;q=0.8",
    })
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            ctype = r.headers.get("Content-Type", "")
            if "html" not in ctype.lower() and "xml" not in ctype.lower():
                # a PDF, an image, a zip — the filename is the best title
                name = urllib.parse.unquote(
                    urllib.parse.urlsplit(url).path.rsplit("/", 1)[-1])
                return {"title": clean(name) or host,
                        "site": host,
                        "desc": clean(ctype.split(";")[0])}
            html = _decode(r.read(MAX_BYTES), ctype)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError,
            ValueError, TimeoutError) as e:
        reason = getattr(e, "code", None) or getattr(e, "reason", None) or e
        return {"error": clean(str(reason))}

    title = _meta(html, "og:title", "twitter:title")
    if not title:
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
        if m:
            title = clean(unescape(re.sub(r"<[^>]+>", "", m.group(1))))
    desc = _meta(html, "og:description", "description", "twitter:description")
    site = _meta(html, "og:site_name") or host
    return {"title": title, "desc": desc, "site": site}


def title_fallback(url: str) -> str:
    """Something readable when the page can't be reached."""
    u = urllib.parse.urlsplit(url)
    path = u.path.strip("/")
    if path:
        last = urllib.parse.unquote(path.rsplit("/", 1)[-1])
        last = re.sub(r"\.(html?|php|aspx?|pdf)$", "", last, flags=re.I)
        last = re.sub(r"[-_+]+", " ", last).strip()
        if len(last) > 2 and not last.isdigit():
            return clean(last[:110])
        # A one-character or numeric segment is no title at all. Domain plus
        # path is ugly but it's at least distinct, which matters: two links
        # on one domain must not land on the same filename.
        return clean(f"{domain(url)}{u.path}")[:110]
    return domain(url)


# ------------------------------------------------------------- the note files

def filename_for(title: str, url: str) -> str:
    """A readable, legal filename. The URL is still the real identity — this
    is only what shows up in the file list."""
    name = BAD_FILENAME.sub(" ", clean(title))
    name = re.sub(r"\s+", " ", name).strip(" .")
    if len(name) > 80:
        name = name[:80].rsplit(" ", 1)[0].strip(" .") or name[:80]
    if not name:
        name = BAD_FILENAME.sub("-", domain(url)) or "link"
    if name.lower() == "links":       # never collide with the index note
        name = f"{name} ({domain(url)})"
    return name


def yaml_value(s: str) -> str:
    """Quote a frontmatter value if plain YAML would choke on it.

    Page titles are full of colons — `POV: You're an AI Born 9 Seconds Ago`
    written unquoted is invalid YAML, and Obsidian would drop the whole
    frontmatter block, taking the Bases view with it."""
    s = clean(s)
    if s == "":
        return '""'
    risky = (s[0] in "-?:,[]{}#&*!|>'\"%@`"
             or ": " in s or s.endswith(":") or " #" in s
             or s.lower() in ("true", "false", "null", "yes", "no", "on", "off")
             or re.fullmatch(r"[\d.+\-eE]+", s) is not None)
    if risky:
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return s


def yaml_unquote(v: str) -> str:
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        inner = v[1:-1]
        if v[0] == '"':
            inner = inner.replace('\\"', '"').replace("\\\\", "\\")
        return inner
    return v


def split_front(text: str):
    """(frontmatter dict, body). Values stay strings; `tags` becomes a list."""
    fm, body = {}, text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            block = text[3:end]
            body = text[end + 4:].lstrip("\n")
            key = None
            for raw in block.split("\n"):
                if re.match(r"^\s*-\s+", raw) and key:
                    fm.setdefault(key + "_list", []).append(
                        yaml_unquote(raw.split("-", 1)[1]))
                elif ":" in raw:
                    key, val = raw.split(":", 1)
                    key = key.strip()
                    if key:
                        fm[key] = yaml_unquote(val)
    fm["tags"] = fm.pop("tags_list", [])
    return fm, body


def read_note(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    fm, _ = split_front(text)
    if not fm.get("url"):
        return {}
    return {
        "path": path,
        "text": text,
        "title": fm.get("title") or path.stem,
        "url": fm.get("url", ""),
        "site": fm.get("site", ""),
        "what": fm.get("what", ""),
        "saved": fm.get("saved", ""),
        "status": (fm.get("status") or "unread").lower(),
        "tags": [t for t in fm.get("tags", []) if t != "link"],
    }


def all_links() -> list:
    """Every link note in the folder, oldest first. The notes are the truth."""
    if not LINKS_DIR.is_dir():
        return []
    out = []
    for p in sorted(LINKS_DIR.glob("*.md")):
        if p.name == INDEX.name:
            continue
        rec = read_note(p)
        if rec:
            out.append(rec)
    out.sort(key=lambda r: (r["saved"], r["title"].lower()))
    return out


def render_note(rec: dict, keep_body: str = "") -> str:
    """Frontmatter + the generated block + whatever was already there."""
    tags = "\n".join(f"  - {t}" for t in ["link"] + rec["tags"])
    what = rec["what"] or "_No description — the page didn't give one._"
    front = (
        "---\n"
        f"title: {yaml_value(rec['title'])}\n"
        f"tags:\n{tags}\n"
        f"url: {yaml_value(rec['url'])}\n"
        f"site: {yaml_value(rec['site'])}\n"
        f"what: {yaml_value(rec['what'])}\n"
        f"saved: {rec['saved']}\n"
        f"status: {rec['status']}\n"
        "---\n\n"
    )
    generated = (
        f"# {rec['title']}\n\n"
        f"{NOTE_BEGIN}\n"
        f"<{rec['url']}>\n\n"
        f"**{rec['site']}** · saved {rec['saved']} · `{rec['status']}`\n\n"
        f"> {what}\n"
        f"{NOTE_END}\n\n"
    )
    body = keep_body or (
        f"{MY_NOTES}\n\n\n"
        "## Related\n\n"
        "- [[Links]]\n"
    )
    return front + generated + body


def human_half(text: str) -> str:
    """Everything from `## My notes` down — never rewritten."""
    i = text.find(MY_NOTES)
    return text[i:] if i != -1 else ""


def save_note(rec: dict, existing: Path = None) -> Path:
    path = existing
    if path is None:
        # Two different links can want the same filename — a page with no
        # usable title, or genuinely identical titles on two sites. Taking
        # the name would silently overwrite the other note, so number it
        # instead. The URL in the frontmatter stays the real identity.
        stem = filename_for(rec["title"], rec["url"])
        path = LINKS_DIR / f"{stem}.md"
        n = 2
        while path.exists():
            if read_note(path).get("url") == rec["url"]:
                break                      # same link — this is its note
            path = LINKS_DIR / f"{stem} ({n}).md"
            n += 1
    keep = ""
    if path.exists():
        keep = human_half(path.read_text(encoding="utf-8"))
    write_atomic(path, render_note(rec, keep))
    return path


# ----------------------------------------------------------------- the index

INDEX_HEADER = f"""---
title: Links
tags:
  - index
---

# Links

One note per link I send. The note holds the URL, what the page is, and an
empty `## My notes` section for whatever I want to add later.

> [!info] How this fills up
> I paste a link, the AI runs `AIOS/scripts/link.py` on it. I never have to
> say "save this". The script fetches the page so the note says what the link
> actually *is*, not just where it points.
>
> Statuses: `unread` (default) · `read` · `useful` · `dead`.

![[Links.base]]

## All links

%% Machine-written by `AIOS/scripts/link.py` from the notes in this folder.
Don't hand-edit the table — edit the note, then run `link.py --rebuild`. %%

{INDEX_BEGIN}
{INDEX_END}

## Related

- [[Atlas]]
- [[Radar]] — things I want to check out, as a queue
- [[Clippings]] — the ones worth a full summary note
"""

BASE_FILE = """filters:
  and:
    - file.inFolder("Atlas/Links")
    - file.ext == "md"
    - '!file.hasTag("index")'
properties:
  file.name:
    displayName: Link
  what:
    displayName: What it is
  site:
    displayName: Site
  status:
    displayName: Status
  saved:
    displayName: Saved
views:
  - type: table
    name: Unread
    filters:
      and:
        - status == "unread"
    order:
      - file.name
      - what
      - site
      - saved
  - type: table
    name: Everything
    groupBy:
      property: status
      direction: ASC
    order:
      - file.name
      - what
      - site
      - status
      - saved
  - type: table
    name: Worth keeping
    filters:
      and:
        - status == "useful"
    order:
      - file.name
      - what
      - site
      - saved
  - type: table
    name: Dead
    filters:
      and:
        - status == "dead"
    order:
      - file.name
      - site
      - saved
"""


def index_table(rows: list) -> str:
    out = [f"| {' | '.join(COLUMNS)} |",
           "|" + "|".join(["---"] * len(COLUMNS)) + "|"]
    for r in sorted(rows, key=lambda x: (x["saved"], x["title"].lower()),
                    reverse=True):
        note = r["path"].stem
        out.append(f"| [[{note}]] | {cell(r['what'])} | {cell(r['site'])} | "
                   f"{r['saved']} | {r['status']} |")
    if not rows:
        out.append(f"| _nothing saved yet_ |{' |' * (len(COLUMNS) - 1)}")
    return "\n".join(out)


def rebuild_index(quiet=False) -> int:
    LINKS_DIR.mkdir(parents=True, exist_ok=True)
    if not BASE.exists():
        write_atomic(BASE, BASE_FILE)
    if not INDEX.exists():
        write_atomic(INDEX, INDEX_HEADER)
    text = INDEX.read_text(encoding="utf-8")
    rows = all_links()
    table = index_table(rows)
    if INDEX_BEGIN in text and INDEX_END in text:
        head = text.split(INDEX_BEGIN)[0]
        tail = text.split(INDEX_END, 1)[1]
        new = f"{head}{INDEX_BEGIN}\n{table}\n{INDEX_END}{tail}"
    else:
        # markers gone (hand-edited away) — put them back without losing prose
        new = text.rstrip() + f"\n\n## All links\n\n{INDEX_BEGIN}\n{table}\n{INDEX_END}\n"
        print("link: index markers were missing — re-added them", file=sys.stderr)
    if new != text:
        write_atomic(INDEX, new)
    if not quiet:
        print(f"link: index rebuilt — {len(rows)} link(s) → {P.relative(INDEX)}")
    return len(rows)


def log(entries: list):
    """One receipt per saved link in today's `## Changes`."""
    if not entries:
        return
    payload = "".join(entries)
    try:
        subprocess.run(
            [sys.executable or "python3", str(P.SCRIPTS / "logchange.py"),
             "--stdin"],
            input=payload, text=True, check=False, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as e:
        print(f"link: WARNING — logchange did not run ({e}). "
              f"The link is saved; the receipt is not.", file=sys.stderr)


def receipt(what: str, path: Path, kind: str = "append") -> str:
    return f"{what}\t{P.relative(path)}\t{kind}\n"


# ------------------------------------------------------------------- commands

def cmd_add(args) -> int:
    urls = []
    for raw in args.urls:
        # A positional argument is usually one URL, but a whole pasted
        # message works too — so pull every URL out of it, and only fall
        # back to normalising the raw string if the regex found nothing (a
        # bare `example.com/thing` with no scheme and no www).
        found = extract_urls(raw)
        urls.extend(found or [normalize(raw)])
    if args.from_text:
        urls.extend(extract_urls(args.from_text))
    urls = [u for u in dict.fromkeys(urls) if u]
    if not urls:
        fail("no usable URL found in that")

    LINKS_DIR.mkdir(parents=True, exist_ok=True)
    known = {r["url"]: r for r in all_links()}
    today = date.today().isoformat()
    tags = [t.lstrip("#") for t in (args.tag or [])]
    status = (args.status or "unread").lower()
    if status not in STATUSES:
        fail(f"status must be one of {', '.join(STATUSES)}")

    receipts, added, updated = [], [], []
    for url in urls:
        old = known.get(url)
        if old:
            changed = []
            if args.why and args.why not in old["what"]:
                old["what"] = clean(f"{old['what']} · {args.why}").strip(" ·")
                changed.append("description")
            new_tags = [t for t in tags if t not in old["tags"]]
            if new_tags:
                old["tags"] += new_tags
                changed.append("tags")
            if args.status and status != old["status"]:
                old["status"] = status
                changed.append("status")
            if changed:
                save_note(old, existing=old["path"])
                receipts.append(receipt(
                    f"Updated saved link ({', '.join(changed)}): "
                    f"{old['title']} — {url}", old["path"]))
            updated.append((old, changed))
            continue

        meta = {} if args.no_fetch else fetch_meta(url)
        if meta.get("error"):
            title = title_fallback(url)
            what = clean(args.why) or f"couldn't reach it ({meta['error']})"
            site = domain(url)
        else:
            title = meta.get("title") or title_fallback(url)
            site = clean(meta.get("site") or domain(url))
            what = clean(args.why) or clean(meta.get("desc") or "")
        if len(what) > 300:
            what = what[:297].rstrip() + "…"
        if len(title) > 150:
            title = title[:147].rstrip() + "…"

        rec = {"url": url, "title": title, "site": site, "what": what,
               "tags": list(tags), "saved": today, "status": status}
        rec["path"] = save_note(rec)
        known[url] = rec
        added.append(rec)
        receipts.append(receipt(
            f"Saved link: {title} ({site}) — {url}", rec["path"], "new"))

    rebuild_index(quiet=True)

    for r in added:
        print(f"link: saved — {r['title']}  [{r['site']}]")
        print(f"      {r['url']}")
        print(f"      note: {P.relative(r['path'])}")
        if r["what"]:
            print(f"      {r['what'][:110]}")
        tr = pull_transcript(r["url"])
        if tr is not None:
            path, words = tr
            if path:
                print(f"      transcript: {P.relative(path)}  ({words} words)")
                print("      ^^ READ IT before writing a word about this video.")
            else:
                print("      !! NO TRANSCRIPT — this video was NOT watched.")
                print("      Do not describe it. Say you couldn't watch it.")
    for old, changed in updated:
        if changed:
            print(f"link: already saved, updated {', '.join(changed)} — "
                  f"{old['title']}")
        else:
            print(f"link: already saved, nothing to change — {old['title']}")
    log(receipts)
    return 0


def cmd_list(args) -> int:
    rows = all_links()
    if args.status_filter:
        rows = [r for r in rows if r["status"] == args.status_filter.lower()]
    if not rows:
        print("link: nothing saved yet")
        return 0
    n = args.list if isinstance(args.list, int) and args.list > 0 else 20
    for r in reversed(rows[-n:]):
        print(f"{r['saved']}  [{r['status']:6s}] {r['title']}")
        print(f"                     {r['url']}")
    print(f"\nlink: {len(rows)} saved in total → {P.relative(LINKS_DIR)}/")
    return 0


def cmd_find(args) -> int:
    needle = args.find.lower()
    rows = [r for r in all_links()
            if needle in " ".join([r["title"], r["url"], r["what"],
                                   r["site"], " ".join(r["tags"])]).lower()]
    if not rows:
        print(f"link: no saved link matches {args.find!r}")
        return 1
    for r in rows:
        print(f"{r['saved']}  [{r['status']:6s}] {r['title']}")
        print(f"                     {r['url']}")
        print(f"                     {P.relative(r['path'])}")
    return 0


def cmd_set(args) -> int:
    needle, status = args.set[0].lower(), args.set[1].lower()
    if status not in STATUSES:
        fail(f"status must be one of {', '.join(STATUSES)}")
    hits = [r for r in all_links()
            if needle in (r["title"] + " " + r["url"]).lower()]
    if not hits:
        fail(f"no saved link matches {args.set[0]!r}")
    if len(hits) > 1 and not args.all:
        print(f"link: {args.set[0]!r} matches {len(hits)} links — "
              f"be more specific, or pass --all:")
        for r in hits:
            print(f"  {r['title']}  {r['url']}")
        return 1
    for r in hits:
        r["status"] = status
        save_note(r, existing=r["path"])
        print(f"link: {r['title']} → {status}")
    rebuild_index(quiet=True)
    log([receipt(f"Link status → {status}: {r['title']}", r["path"])
         for r in hits])
    return 0


def cmd_check(args) -> int:
    """Re-test every saved link. Marks dead ones, fills in missing titles."""
    rows = all_links()
    if not rows:
        print("link: nothing saved yet")
        return 0
    dead, revived, retitled = [], [], []
    for r in rows:
        meta = fetch_meta(r["url"])
        if meta.get("error"):
            if r["status"] != "dead":
                r["status"] = "dead"
                r["what"] = clean(f"{r['what']} · dead {date.today()} "
                                  f"({meta['error']})").strip(" ·")
                dead.append(r)
            else:
                continue
        else:
            good = meta.get("title")
            touched = False
            if r["status"] == "dead":
                r["status"] = "unread"
                revived.append(r)
                touched = True
            if good and (r["title"] == domain(r["url"]) or not r["title"]):
                r["title"] = good[:150]
                retitled.append(r)
                touched = True
            if not touched:
                continue
        save_note(r, existing=r["path"])
    rebuild_index(quiet=True)
    print(f"link: checked {len(rows)} — {len(dead)} newly dead, "
          f"{len(revived)} back up, {len(retitled)} retitled")
    for r in dead:
        print(f"  DEAD  {r['title']}  {r['url']}")
    receipts = [receipt(f"Link marked dead: {r['title']} — {r['url']}",
                        r["path"]) for r in dead]
    receipts += [receipt(f"Link back up: {r['title']}", r["path"])
                 for r in revived]
    receipts += [receipt(f"Filled in real title: {r['title']}", r["path"])
                 for r in retitled]
    log(receipts)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="link.py",
        description="Save a link as its own note in Atlas/Links/.")
    ap.add_argument("urls", nargs="*", help="one or more URLs")
    ap.add_argument("--why", help="what it is / why it's worth keeping "
                                  "(overrides the page's own description)")
    ap.add_argument("--tag", action="append",
                    help="tag it (repeatable): --tag linux --tag server")
    ap.add_argument("--status", choices=STATUSES, help="default: unread")
    ap.add_argument("--from-text", metavar="TEXT",
                    help="pull every URL out of a pasted blob of text")
    ap.add_argument("--no-fetch", action="store_true",
                    help="skip the page fetch (offline, or in a hurry)")
    ap.add_argument("--list", nargs="?", type=int, const=20, metavar="N",
                    help="show the newest N saved links (default 20)")
    ap.add_argument("--status-filter", metavar="STATUS",
                    help="with --list: only this status")
    ap.add_argument("--find", metavar="TEXT", help="search saved links")
    ap.add_argument("--set", nargs=2, metavar=("MATCH", "STATUS"),
                    help="set a link's status: --set arch read")
    ap.add_argument("--all", action="store_true",
                    help="with --set: apply to every match, not just one")
    ap.add_argument("--check", action="store_true",
                    help="re-test every saved link, mark dead ones")
    ap.add_argument("--rebuild", action="store_true",
                    help="regenerate the index table from the notes")
    args = ap.parse_args()

    if args.rebuild:
        rebuild_index()
        return 0
    if args.check:
        return cmd_check(args)
    if args.set:
        return cmd_set(args)
    if args.find:
        return cmd_find(args)
    if args.list is not None:
        return cmd_list(args)
    if args.urls or args.from_text:
        return cmd_add(args)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
