#!/usr/bin/env python3
"""
shot.py — stamp a screenshot so it can never lose its story.

THE PROBLEM: an image in the vault is a bare file. Six months later it is a
picture of something, from somewhere, from some conversation, and nothing on
disk says which. The filename gives a date at best.

This script attaches the same facts in THREE places, so losing one doesn't
lose the picture's meaning:

  1. INSIDE THE IMAGE FILE — PNG tEXt/iTXt chunks, JPEG comment segment.
     Survives being emailed, uploaded, copied out of the vault entirely.
     The pixels are not touched. Nothing is drawn on the picture.
  2. A SIDECAR NOTE next to it — `<same name>.md`. This is what Obsidian
     shows: the image embedded, when it was made, which chat it came from,
     what was read off it, what it links to.
  3. A ROW in AIOS/history/screenshots/Screenshots.md — the browsable index.

Where a screenshot lives
-------------------------
Drop a raw screenshot in Inbox/Screenshots/ (or anywhere else — a chat
upload, a Downloads folder) and point this script at it. If the image is
already inside the vault it gets MOVED into AIOS/history/screenshots/ under
this script's own naming convention; if it comes from outside the vault it
gets COPIED in. Either way Inbox/Screenshots/ ends up empty again once
you're done — this script IS the "dealt with" that Inbox/Inbox.md promises,
for the screenshot case specifically. AIOS/history/screenshots/ is the
permanent, indexed home afterwards — not itself an inbox, nothing there is
expected to be emptied.

Chats that aren't backed up yet
--------------------------------
Chat transcripts land in AIOS/history/chat-history/cowork/ on a delay (see
backup-cowork.py), so a screenshot sent *during* a live chat belongs to a
transcript that does not exist yet. Linking it would be a broken link. So the
sidecar records the chat's name, its id, and the path the transcript WILL
have, marked `chat_saved: false`.

    python3 AIOS/scripts/shot.py --relink

turns every one of those into a real wikilink once the backup has run. That
is the "connection for the future chat": written now, joined up later, by a
script rather than by somebody remembering.

Usage
-----
    # register an image (the common case)
    python3 AIOS/scripts/shot.py IMAGE --shows "what it shows" \
        --chat "chat title" --chat-id local_902b1e6f-... \
        --taken "2026-08-09 19:30" --extracted "mod list -> Atlas/Worlds/..."

    python3 AIOS/scripts/shot.py --read IMAGE     # dump embedded metadata
    python3 AIOS/scripts/shot.py --check          # images with no sidecar
    python3 AIOS/scripts/shot.py --relink         # join up saved chats

Exits non-zero on failure, so a caller can tell "stamped" from "silently did
nothing". No dependencies. Plain stdlib.
"""
import scriptlog  # noqa: F401 -- logs this run to AIOS/history/scripts/

# aios-run: agent  (called for every picture sent)

import argparse
import datetime as dt
import os
import re
import shutil
import struct
import subprocess
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P  # noqa: E402

VAULT = P.VAULT
SHOTS = VAULT / "AIOS" / "history" / "screenshots"
INDEX = SHOTS / "Screenshots.md"
COWORK = P.HISTORY_COWORK
LOGCHANGE = VAULT / "AIOS" / "scripts" / "logchange.py"

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".heic", ".svg"}
SKIP_DIRS = {"Privat", ".git", ".obsidian", ".trash", ".claude", "skills"}

# Keys written into the image itself. Title/Description/Source/Comment/
# Creation Time/Software are the PNG spec's own registered keywords, so
# ordinary image viewers show them. The rest are ours.
STAMP_ORDER = ["Title", "Description", "Creation Time", "Source", "Chat",
               "Chat ID", "Chat Note", "Vault Note", "Extracted", "Software",
               "Comment"]

# Internal watermark used to find and replace THIS script's own previous
# stamp on re-run, and to tell it apart from any other JPEG comment.
MARK = "shot.py"


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------

def die(msg):
    print(f"shot.py: {msg}", file=sys.stderr)
    sys.exit(1)


def slugify(text, maxlen=60):
    text = re.sub(r"[^\w\s-]", "", text.lower(), flags=re.U)
    text = re.sub(r"[\s_]+", "-", text).strip("-")
    if len(text) > maxlen:
        text = text[:maxlen].rsplit("-", 1)[0]
    return text or "screenshot"


def parse_when(s, fallback=None):
    """Accept 'YYYY-MM-DD HH:MM', 'YYYY-MM-DDTHH:MM', 'YYYY-MM-DD' or 'now'."""
    if not s:
        return fallback
    s = s.strip()
    if s.lower() == "now":
        return dt.datetime.now()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(s, fmt)
        except ValueError:
            continue
    die(f"can't read a date out of {s!r}. Use YYYY-MM-DD HH:MM.")


def short_id(chat_id):
    """local_902b1e6f-33ac-... -> 902b1e6f. Matches how backup-cowork.py names
    transcripts (date + first 8 chars of the session file's stem)."""
    if not chat_id:
        return ""
    cid = chat_id.strip()
    for prefix in ("local_", "session_"):
        if cid.startswith(prefix):
            cid = cid[len(prefix):]
    return cid[:8]


def find_transcript(id8):
    """The real transcript for this chat, if the backup has already run."""
    if not id8 or not COWORK.is_dir():
        return None
    # backup-cowork.py writes transcripts flat as `<date>-<id8>.md` directly
    # under AIOS/history/chat-history/cowork/ — no subfolders to search.
    hits = sorted(COWORK.glob(f"*-{id8}.md"))
    return hits[-1] if hits else None


def rel(p):
    try:
        return str(Path(p).resolve().relative_to(VAULT))
    except ValueError:
        return str(p)


def logchange(what, path, kind="new"):
    if not LOGCHANGE.exists():
        return False
    r = subprocess.run([sys.executable, str(LOGCHANGE), what, str(path),
                        "--kind", kind], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"shot.py: logchange failed: {r.stderr.strip()}", file=sys.stderr)
    return r.returncode == 0


# --------------------------------------------------------------------------
# writing metadata INTO the image file
# --------------------------------------------------------------------------

def _png_chunk(ctype, payload):
    crc = zlib.crc32(ctype + payload) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + ctype + payload + \
        struct.pack(">I", crc)


def _png_text_chunk(key, value):
    kb = key.encode("latin-1", "replace")
    try:
        return _png_chunk(b"tEXt", kb + b"\x00" + value.encode("latin-1"))
    except UnicodeEncodeError:
        # iTXt carries UTF-8: keyword \0 compflag compmethod lang \0 transkw \0 text
        payload = (kb + b"\x00\x00\x00" + b"\x00" + b"\x00" +
                   value.encode("utf-8"))
        return _png_chunk(b"iTXt", payload)


def png_stamp(path, meta):
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return False
    out = bytearray(data[:8])
    pos, new_chunks = 8, b"".join(
        _png_text_chunk(k, v) for k, v in meta.items() if v)
    inserted = False
    while pos + 8 <= len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        ctype = data[pos + 4:pos + 8]
        end = pos + 8 + length + 4
        if end > len(data):
            return False   # truncated/corrupt PNG - never write it back
        chunk = data[pos:end]
        pos = end
        if ctype in (b"tEXt", b"iTXt", b"zTXt"):
            kw = chunk[8:].split(b"\x00", 1)[0].decode("latin-1", "replace")
            if kw in meta:            # drop our own previous stamp
                continue
        out += chunk
        if ctype == b"IHDR" and not inserted:
            out += new_chunks
            inserted = True
    if not inserted:
        return False
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(bytes(out))
    os.replace(tmp, path)
    return True


def jpeg_stamp(path, meta):
    data = path.read_bytes()
    if data[:2] != b"\xff\xd8":
        return False
    text = "\n".join(f"{k}: {v}" for k, v in meta.items() if v)
    payload = (MARK + "\n" + text).encode("utf-8")
    com = b"\xff\xfe" + struct.pack(">H", len(payload) + 2) + payload
    out, pos = bytearray(data[:2]), 2
    while pos + 4 <= len(data):
        if data[pos] != 0xFF:
            break
        marker = data[pos + 1]
        if marker == 0xDA:                      # start of scan — image data
            break
        seglen = struct.unpack(">H", data[pos + 2:pos + 4])[0]
        seg = data[pos:pos + 2 + seglen]
        pos += 2 + seglen
        if marker == 0xFE and MARK.encode() in seg[:32]:
            continue                            # drop our previous stamp
        out += seg
    out = bytearray(data[:2]) + com + out[2:] + data[pos:]
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(bytes(out))
    os.replace(tmp, path)
    return True


def stamp_image(path, meta):
    """Returns 'png' | 'jpeg' | '' (format can't carry metadata)."""
    ext = path.suffix.lower()
    try:
        if ext == ".png" and png_stamp(path, meta):
            return "png"
        if ext in (".jpg", ".jpeg") and jpeg_stamp(path, meta):
            return "jpeg"
    except Exception as e:                       # never lose the picture
        print(f"shot.py: could not stamp {path.name}: {e}", file=sys.stderr)
    return ""


def read_stamp(path):
    """Pull metadata back out of an image. Proof the stamp actually stuck."""
    data = path.read_bytes()
    found = []
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        pos = 8
        while pos + 8 <= len(data):
            length = struct.unpack(">I", data[pos:pos + 4])[0]
            ctype = data[pos + 4:pos + 8]
            body = data[pos + 8:pos + 8 + length]
            pos += 8 + length + 4
            if ctype == b"tEXt":
                k, _, v = body.partition(b"\x00")
                found.append((k.decode("latin-1"), v.decode("latin-1")))
            elif ctype == b"iTXt":
                k, _, restofit = body.partition(b"\x00")
                parts = restofit[2:].split(b"\x00", 2)
                if len(parts) == 3:
                    found.append((k.decode("latin-1"),
                                  parts[2].decode("utf-8", "replace")))
    elif data[:2] == b"\xff\xd8":
        pos = 2
        while pos + 4 <= len(data) and data[pos] == 0xFF:
            marker = data[pos + 1]
            if marker == 0xDA:
                break
            seglen = struct.unpack(">H", data[pos + 2:pos + 4])[0]
            if marker == 0xFE:
                txt = data[pos + 4:pos + 2 + seglen].decode("utf-8", "replace")
                for line in txt.splitlines()[1:]:
                    k, _, v = line.partition(": ")
                    found.append((k, v))
            pos += 2 + seglen
    return found


# --------------------------------------------------------------------------
# the sidecar note
# --------------------------------------------------------------------------

def chat_block(chat, id8, transcript, taken):
    """Text describing which chat this came from — a real wikilink if the
    transcript exists, a marked-pending pointer if the backup hasn't run."""
    if transcript:
        return (f"Sent in **[[{transcript.stem}|{chat or 'a chat'}]]** "
                f"(`{rel(transcript)}`).")
    if id8:
        # A future path, not a real one, spelled out on purpose: backup-cowork
        # runs on a delay, so the transcript doesn't exist at the moment this
        # is written. Guessing at a wikilink here would write a wrong fact
        # into a note, and wrong facts in notes are the thing this vault is
        # most careful about.
        future = f"AIOS/history/chat-history/cowork/{taken:%Y-%m-%d}-{id8}.md"
        return (f"Sent in the chat **{chat or 'untitled'}** "
                f"(id `{id8}`). That chat was still open when this was saved, "
                f"so its transcript did not exist yet — it will be written to "
                f"`{future}` once backup-cowork.py next runs. Run "
                f"`python3 AIOS/scripts/shot.py --relink` afterwards and this "
                f"turns into a real link by itself.")
    return f"Source: {chat or 'unknown'}."


def write_sidecar(img, meta, args, transcript, taken, added, id8):
    note = img.with_suffix(".md")
    tags = ["screenshot", "inbox"] + list(args.tags or [])
    fm = ["---", f"title: {img.stem}", "tags:"]
    fm += [f"  - {t}" for t in dict.fromkeys(tags)]
    fm += [
        f"image: {img.name}",
        f"taken: {taken:%Y-%m-%d %H:%M}",
        f"added: {added:%Y-%m-%d %H:%M}",
        f'source: "{args.source}"',
        f'chat: "{(args.chat or "").replace(chr(34), chr(39))}"',
        f"chat_id: {id8}",
        f"chat_note: {rel(transcript) if transcript else ''}",
        f"chat_saved: {'true' if transcript else 'false'}",
        f"confirmed: {added:%Y-%m-%d}",
        "---",
        "",
        f"# {args.shows}",
        "",
        f"![[{img.name}]]",
        "",
        "## When",
        "",
        f"- **Made:** {taken:%A %-d %B %Y, %H:%M}",
        f"- **Saved into the vault:** {added:%A %-d %B %Y, %H:%M}",
        "",
        "## Where it came from",
        "",
        chat_block(args.chat, id8, transcript, taken),
        "",
        "## What it shows",
        "",
        args.shows,
        "",
        "## What was read off it",
        "",
        args.extracted or "_Nothing extracted yet — this image has not been "
                          "processed._",
        "",
    ]
    fm += ["## Related", ""]
    fm += [f"- [[{r}]]" for r in (args.related or [])]
    fm += ["- [[Screenshots]]", "- [[Inbox]]", ""]
    note.write_text("\n".join(fm), encoding="utf-8")
    return note


# --------------------------------------------------------------------------
# the index row
# --------------------------------------------------------------------------

def cell(text):
    """Make arbitrary text safe inside a Markdown table cell.

    A raw `|` ends the cell early and silently shifts every column after it —
    exactly what a `curl ... | bash` command sitting in a `--shows` string
    would do. Newlines do the same to the row.
    """
    text = " ".join(str(text).split())
    return text.replace("\\|", "|").replace("|", "\\|")


def index_row(img, args, taken, transcript, id8):
    if transcript:
        frm = f"{args.source} — [[{transcript.stem}\\|{args.chat or 'chat'}]]"
    elif args.chat or id8:
        frm = (f"{cell(args.source)} — {cell(args.chat or 'untitled')} "
               f"(`{id8}`, not backed up yet)")
    else:
        frm = cell(args.source)
    proc = cell(args.extracted) or "**Not processed yet**"
    return (f"| {taken:%Y-%m-%d %H:%M} | [[{img.stem}]] | {cell(args.shows)} "
            f"| {frm} | {proc} |")


def add_index_row(row, img_stem):
    """Insert a row as the FIRST data row of the index table.

    Anchored to the table's own header separator (`| --- | --- | ...`) rather
    than a marker comment elsewhere in the file — a marker's position can
    drift out of sync with the table (a blank line between the marker and
    the last row reads to Markdown as the end of one table and the start of
    a second, headerless one), but the separator can't drift, because it IS
    the table.
    """
    if not INDEX.exists():
        die(f"{rel(INDEX)} is missing — refusing to invent the index.")
    lines = INDEX.read_text(encoding="utf-8").splitlines()

    # replace an existing row for the same image rather than duplicating it
    lines = [l for l in lines
             if not (l.startswith("| ") and f"[[{img_stem}]]" in l)]

    # find the header separator row: | --- | --- | ...
    sep = next((i for i, l in enumerate(lines)
                if re.fullmatch(r"\|(\s*:?-{2,}:?\s*\|)+", l.strip())), None)
    if sep is None:
        die(f"{rel(INDEX)} has no table header; not guessing where rows go.")

    # collect the existing data rows, drop blank lines inside the table
    end = sep + 1
    body = []
    while end < len(lines):
        l = lines[end]
        if l.startswith("| "):
            body.append(l)
            end += 1
        elif not l.strip() and end + 1 < len(lines) and \
                lines[end + 1].startswith("| "):
            end += 1                      # blank line between rows: swallow it
        else:
            break

    body.append(row)
    # newest first, by the timestamp in the Added column
    body.sort(key=lambda l: l.split("|")[1].strip(), reverse=True)

    lines[sep + 1:end] = body
    INDEX.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------

def cmd_register(args):
    src = Path(args.image).expanduser()
    if not src.exists():
        die(f"no such file: {src}")
    if src.suffix.lower() not in IMAGE_EXTS:
        die(f"{src.name} is not an image ({src.suffix or 'no extension'}).")

    taken = parse_when(args.taken,
                       dt.datetime.fromtimestamp(src.stat().st_mtime))
    added = parse_when(args.added, dt.datetime.now())
    id8 = short_id(args.chat_id)
    transcript = find_transcript(id8)

    # Land it in AIOS/history/screenshots/ under the naming convention. If
    # it's already somewhere inside the vault (e.g. Inbox/Screenshots/) it's
    # MOVED here, which is what empties the inbox; from outside the vault
    # (a chat upload, Downloads/) it's COPIED in instead.
    inside = VAULT in src.resolve().parents
    dest_dir = src.parent if inside else SHOTS
    dest_dir.mkdir(parents=True, exist_ok=True)
    name = f"{taken:%Y-%m-%d-%H%M}-{slugify(args.shows)}{src.suffix.lower()}"
    dest = dest_dir / (src.name if args.keep_name else name)
    if dest.resolve() != src.resolve():
        if dest.exists():
            dest = dest_dir / f"{dest.stem}-2{dest.suffix}"
        if inside:
            src.rename(dest)
        else:
            shutil.copy2(src, dest)
    old_sidecar = src.with_suffix(".md")
    if inside and old_sidecar.exists() and old_sidecar != dest.with_suffix(".md"):
        old_sidecar.unlink()

    meta = {
        "Title": args.shows,
        "Description": args.shows,
        "Creation Time": f"{taken:%Y-%m-%d %H:%M}",
        "Source": args.source,
        "Chat": args.chat or "",
        "Chat ID": id8,
        "Chat Note": (rel(transcript) if transcript else
                      (f"AIOS/history/chat-history/cowork/{taken:%Y-%m-%d}-{id8}.md "
                       f"(pending backup)" if id8 else "")),
        "Vault Note": rel(dest.with_suffix(".md")),
        "Extracted": args.extracted or "",
        "Software": MARK,
        "Comment": (f"Saved into the vault {added:%Y-%m-%d %H:%M}. "
                    f"Full context: {rel(dest.with_suffix('.md'))}"),
    }
    meta = {k: meta.get(k, "") for k in STAMP_ORDER}
    stamped = stamp_image(dest, meta)

    note = write_sidecar(dest, meta, args, transcript, taken, added, id8)
    add_index_row(index_row(dest, args, taken, transcript, id8), dest.stem)

    if not args.no_log:
        logchange(f"Screenshot stamped: {args.shows} — "
                  f"{'metadata embedded in the file, ' if stamped else ''}"
                  f"sidecar note + row in Screenshots.md",
                  rel(note), kind="new")

    print(f"stamped   {rel(dest)}")
    print(f"  embedded in file: {stamped or 'NO (format cannot carry text)'}")
    print(f"  sidecar note:     {rel(note)}")
    print(f"  chat:             "
          f"{args.chat or '(none given)'} "
          f"{'-> ' + rel(transcript) if transcript else '(transcript pending)'}")
    return 0


def cmd_read(args):
    p = Path(args.read).expanduser()
    if not p.exists():
        die(f"no such file: {p}")
    found = read_stamp(p)
    print(f"{rel(p)} — {len(found)} embedded field(s)")
    for k, v in found:
        print(f"  {k}: {v}")
    note = p.with_suffix(".md")
    print(f"  [sidecar] {rel(note)}"
          f"{'' if note.exists() else '  ** MISSING **'}")
    return 0 if found or note.exists() else 1


def all_images():
    for dp, dns, fns in os.walk(VAULT):
        dns[:] = [d for d in dns if d not in SKIP_DIRS and
                  not d.startswith(".")]
        for fn in sorted(fns):
            if Path(fn).suffix.lower() in IMAGE_EXTS:
                yield Path(dp) / fn


def cmd_check(args):
    bad = []
    for img in all_images():
        note = img.with_suffix(".md")
        embedded = dict(read_stamp(img)) if img.suffix.lower() in (
            ".png", ".jpg", ".jpeg") else {}
        missing = []
        if not note.exists():
            missing.append("no sidecar note")
        if img.suffix.lower() in (".png", ".jpg", ".jpeg") and \
                "Description" not in embedded:
            missing.append("nothing embedded in the file")
        if missing:
            bad.append((rel(img), ", ".join(missing)))
    if bad:
        print(f"{len(bad)} image(s) carry no record of where they came from:")
        for p, why in bad:
            print(f"  - {p} — {why}")
        print("\nFix with: python3 AIOS/scripts/shot.py <image> "
              "--shows \"...\" --chat \"...\" --chat-id <id>")
        return 1
    print(f"all images stamped ({sum(1 for _ in all_images())} checked)")
    return 0


def cmd_relink(args):
    """Join up screenshots whose chat has since been backed up."""
    changed = []
    for note in sorted(SHOTS.glob("*.md")):
        if note.name == INDEX.name:
            continue
        text = note.read_text(encoding="utf-8")
        if "chat_saved: false" not in text:
            continue
        m = re.search(r"^chat_id:\s*(\S+)\s*$", text, re.M)
        if not m:
            continue
        transcript = find_transcript(m.group(1))
        if not transcript:
            continue
        mc = re.search(r'^chat:\s*"(.*)"\s*$', text, re.M)
        chat = mc.group(1) if mc else ""
        text = text.replace("chat_saved: false", "chat_saved: true")
        text = re.sub(r"^chat_note:.*$", f"chat_note: {rel(transcript)}",
                      text, count=1, flags=re.M)
        body = re.sub(
            r"## Where it came from\n\n.*?\n\n## What it shows",
            f"## Where it came from\n\nSent in "
            f"**[[{transcript.stem}|{chat or 'a chat'}]]** "
            f"(`{rel(transcript)}`).\n\n## What it shows",
            text, flags=re.S)
        note.write_text(body, encoding="utf-8")
        # index row
        if INDEX.exists():
            idx = INDEX.read_text(encoding="utf-8")
            idx = re.sub(
                rf"(\| \[\[{re.escape(note.stem)}\]\] \|[^|]*\| )[^|]*\|",
                rf"\1sent in chat — [[{transcript.stem}\\|{chat or 'chat'}]] |",
                idx, count=1)
            INDEX.write_text(idx, encoding="utf-8")
        img = next((p for p in note.parent.glob(note.stem + ".*")
                    if p.suffix.lower() in IMAGE_EXTS), None)
        if img:
            meta = dict(read_stamp(img))
            if meta:
                meta["Chat Note"] = rel(transcript)
                stamp_image(img, meta)
        changed.append(note.stem)
    if changed:
        print(f"relinked {len(changed)}: {', '.join(changed)}")
        logchange(f"Linked {len(changed)} screenshot(s) to their chat "
                  f"transcript now that the backup has run",
                  rel(INDEX), kind="edit")
    else:
        print("nothing to relink — no screenshot is waiting on a transcript")
    return 0


def main():
    ap = argparse.ArgumentParser(
        description="Stamp a screenshot with when, where and which chat.")
    ap.add_argument("image", nargs="?", help="the image file")
    ap.add_argument("--shows", help="what the picture shows (required)")
    ap.add_argument("--source", default="sent in chat",
                    help="'sent in chat' | 'dropped in the folder' | ...")
    ap.add_argument("--chat", default="", help="the chat's name")
    ap.add_argument("--chat-id", default="", help="chat/session id")
    ap.add_argument("--taken", help="when the screenshot was MADE "
                                    "(YYYY-MM-DD HH:MM). Default: file mtime")
    ap.add_argument("--added", help="when it reached the vault. Default: now")
    ap.add_argument("--extracted", default="",
                    help="facts pulled off it and where they were written")
    ap.add_argument("--related", action="append",
                    help="note to wikilink (repeatable)")
    ap.add_argument("--tags", action="append", help="extra tag (repeatable)")
    ap.add_argument("--keep-name", action="store_true",
                    help="don't rename to the YYYY-MM-DD-HHMM- convention")
    ap.add_argument("--no-log", action="store_true",
                    help="skip the ## Changes receipt")
    ap.add_argument("--read", help="print the metadata embedded in an image")
    ap.add_argument("--check", action="store_true",
                    help="list images carrying no record of their origin")
    ap.add_argument("--relink", action="store_true",
                    help="join pending screenshots to backed-up transcripts")
    args = ap.parse_args()

    if args.read:
        return cmd_read(args)
    if args.check:
        return cmd_check(args)
    if args.relink:
        return cmd_relink(args)
    if not args.image or not args.shows:
        ap.print_help()
        print("\nshot.py: an image and --shows are both required.",
              file=sys.stderr)
        return 2
    return cmd_register(args)


if __name__ == "__main__":
    sys.exit(main())
