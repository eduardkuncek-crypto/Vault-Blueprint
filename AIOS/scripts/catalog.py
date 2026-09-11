#!/usr/bin/env python3
"""
catalog.py -- one grep-able list of what you play/watch/read/own, so an AI
answering "what games do I play" doesn't have to open every note in
Atlas/Media/, Atlas/Worlds/ and every purchase-tracking Effort to find out.

Same shape as taste.py and where.md -- pure extraction, no judgement,
regenerated automatically rather than hand-maintained.

What it reads (all already-structured frontmatter/tables, nothing guessed):
  - Atlas/Media/*.md      -- `type:` (game/anime/manga/show/film/book) +
                             `status:` (playing/watching/reading/finished/
                             dropped/on hold)
  - Atlas/Worlds/*.md     -- `status:` (active/parked/dead/unconfirmed)
  - Efforts/*Purchase*.md -- `status:` (active/planned/upcoming/stalled/
                             parked/done) -- purchases still being decided
  - Atlas/About Me/Money.md `## Ledger` -- rows that aren't a balance check,
                             i.e. real logged transactions -- purchases
                             already made

Regenerated automatically by logchange.py's refresh_catalog() guard, which
fires whenever a write touches one of the folders/files above -- same
mechanism as refresh_taste_profile(). Can also be run by hand:

    python3 AIOS/scripts/catalog.py

No dependencies. Plain stdlib.
"""
from __future__ import annotations
import scriptlog  # noqa: F401 -- logs this run to AIOS/history/scripts/

import datetime as dt
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P  # noqa: E402

VAULT = P.VAULT
OUT = P.GENERATED / "catalog.md"
MEDIA_DIR = P.MEDIA
WORLDS_DIR = P.WORLDS
EFFORTS_DIR = P.EFFORTS
MONEY = P.ABOUT_ME / "Money.md"

# Index notes -- not subjects, skip them.
SKIP_STEMS = {"Media", "Worlds", "Efforts"}

MEDIA_LABELS = {
    "game": "Games",
    "anime": "Anime",
    "manga": "Manga",
    "show": "Shows",
    "film": "Movies",
    "book": "Books",
}
MEDIA_ORDER = ["Games", "Anime", "Manga", "Shows", "Movies", "Books", "Media (other)"]
MEDIA_STATUS_ORDER = ["playing", "watching", "reading", "on hold", "finished", "dropped"]
WORLD_STATUS_ORDER = ["active", "parked", "unconfirmed", "dead"]
PURCHASE_STATUS_ORDER = ["active", "planned", "upcoming", "stalled", "parked", "done"]

FRONT_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


def rel(p: Path) -> str:
    return p.relative_to(VAULT).as_posix()


def frontmatter(text: str) -> dict:
    """Shallow scalar-key parse -- enough for title/type/status, no yaml dep."""
    m = FRONT_RE.match(text)
    if not m:
        return {}
    fm: dict = {}
    for line in m.group(1).splitlines():
        if re.match(r"^\s*-\s+", line) or ":" not in line:
            continue
        key, _, val = line.partition(":")
        fm[key.strip()] = val.strip().strip('"')
    return fm


def tags_of(text: str) -> list[str]:
    m = re.search(r"^tags:\s*\n((?:\s*-\s*.+\n)+)", text, re.MULTILINE)
    if not m:
        return []
    return [ln.strip("- ").strip() for ln in m.group(1).splitlines() if ln.strip()]


def collect_media() -> dict[str, dict[str, list[tuple[str, str]]]]:
    """{category: {status: [(title, path)]}}"""
    out: dict[str, dict[str, list[tuple[str, str]]]] = {}
    if not MEDIA_DIR.is_dir():
        return out
    for p in sorted(MEDIA_DIR.glob("*.md")):
        if p.stem in SKIP_STEMS:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        fm = frontmatter(text)
        title = fm.get("title") or p.stem
        mtype = fm.get("type")
        if not mtype:
            for t in tags_of(text):
                if t in MEDIA_LABELS:
                    mtype = t
                    break
        category = MEDIA_LABELS.get(mtype, "Media (other)")
        status = fm.get("status") or "unknown"
        out.setdefault(category, {}).setdefault(status, []).append((title, rel(p)))
    return out


def collect_worlds() -> dict[str, list[tuple[str, str]]]:
    """{status: [(title, path)]}"""
    out: dict[str, list[tuple[str, str]]] = {}
    if not WORLDS_DIR.is_dir():
        return out
    for p in sorted(WORLDS_DIR.glob("*.md")):
        if p.stem in SKIP_STEMS:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        fm = frontmatter(text)
        title = fm.get("title") or p.stem
        status = fm.get("status") or "unknown"
        out.setdefault(status, []).append((title, rel(p)))
    return out


def collect_purchases_deciding() -> dict[str, list[tuple[str, str]]]:
    """Efforts/*Purchase*.md, still being decided -- {status: [(title, path)]}"""
    out: dict[str, list[tuple[str, str]]] = {}
    if not EFFORTS_DIR.is_dir():
        return out
    for p in sorted(EFFORTS_DIR.glob("*Purchase*.md")):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        fm = frontmatter(text)
        title = fm.get("title") or p.stem
        status = fm.get("status") or "unknown"
        out.setdefault(status, []).append((title, rel(p)))
    return out


LEDGER_ROW_RE = re.compile(r"^\|(.+?)\|(.+?)\|(.+?)\|(.+?)\|(.*?)\|\s*$")


def collect_purchases_bought() -> list[tuple[str, str, str]]:
    """Real logged transactions from Money.md's Ledger -- (date, what, amount).

    Skips 'Balance check' rows (those are stated balances, not purchases) and
    the header/separator rows of the table.
    """
    out: list[tuple[str, str, str]] = []
    if not MONEY.exists():
        return out
    try:
        text = MONEY.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return out
    m = re.search(r"^## Ledger\s*$", text, re.MULTILINE)
    if not m:
        return out
    rest = text[m.end():]
    nxt = re.search(r"^#{1,2} ", rest, re.MULTILINE)
    body = rest[: nxt.start() if nxt else len(rest)]
    for line in body.splitlines():
        row = LEDGER_ROW_RE.match(line)
        if not row:
            continue
        date, what, amount, _balance, _notes = (c.strip() for c in row.groups())
        if date.lower() in ("date", "---") or set(date) <= {"-"}:
            continue
        what_clean = what.strip("* ")
        if "balance check" in what_clean.lower():
            continue
        out.append((date, what_clean, amount))
    return out


def render_status_group(status_order: list[str], groups: dict) -> list[str]:
    lines = []
    seen_statuses = set(groups)
    ordered = [s for s in status_order if s in seen_statuses] + \
              sorted(seen_statuses - set(status_order))
    for status in ordered:
        items = sorted(groups[status])
        lines.append(f"**{status}** ({len(items)})")
        lines.append("")
        for title, path in items:
            stem = Path(path).stem
            lines.append(f"- [[{stem}]]" if title == stem else f"- [[{stem}|{title}]]")
        lines.append("")
    return lines


def render(media, worlds, deciding, bought) -> str:
    today = dt.date.today().isoformat()
    lines = [
        "---",
        "title: catalog",
        "tags:",
        "  - generated",
        "  - index",
        "confirmed: " + today,
        "---",
        "",
        "# catalog.md -- games, anime, shows, worlds and purchases, one grep",
        "",
        "> [!warning] Generated -- do not edit by hand",
        "> Rebuilt by `python3 AIOS/scripts/catalog.py`, which `logchange.py` runs "
        "automatically whenever a write touches `Atlas/Media/`, `Atlas/Worlds/`, "
        "an `Efforts/*Purchase*.md` note, or `Money.md`. Anything typed in here "
        "is gone on the next write.",
        "",
        "**Not read at session start.** Exists to be searched, not loaded:",
        "",
        "```bash",
        'grep -A5 "^## Games" AIOS/generated/catalog.md',
        'grep -i "some title" AIOS/generated/catalog.md',
        "```",
        "",
        f"Rebuilt {today}.",
        "",
    ]

    for cat in MEDIA_ORDER:
        if cat not in media:
            continue
        lines.append(f"## {cat}")
        lines.append("")
        lines.extend(render_status_group(MEDIA_STATUS_ORDER, media[cat]))

    if worlds:
        lines.append("## Worlds & servers")
        lines.append("")
        lines.extend(render_status_group(WORLD_STATUS_ORDER, worlds))

    lines.append("## Purchases -- deciding")
    lines.append("")
    if deciding:
        lines.extend(render_status_group(PURCHASE_STATUS_ORDER, deciding))
    else:
        lines.append("*Nothing open right now.*")
        lines.append("")

    lines.append("## Purchases -- bought")
    lines.append("")
    if bought:
        lines.append("From `Atlas/About Me/Money.md` § Ledger, real transactions only "
                      "(balance checks excluded).")
        lines.append("")
        lines.append("| Date | What | Amount |")
        lines.append("|---|---|---|")
        for date, what, amount in bought:
            lines.append(f"| {date} | {what} | {amount} |")
        lines.append("")
    else:
        lines.append("*No transactions logged in `Money.md` yet -- only balance "
                      "checks so far. Run `money.py` when a real spend comes up "
                      "and it shows up here automatically.*")
        lines.append("")

    lines.append("## Related")
    lines.append("")
    lines.append("- [[Media]]")
    lines.append("- [[Worlds]]")
    lines.append("- [[Efforts]]")
    lines.append("- [[Money]]")
    if (P.GENERATED / "taste.md").exists():
        lines.append("- [[taste]] -- opinions on this stuff, not just the list")
    return "\n".join(lines).rstrip("\n") + "\n"


def main() -> int:
    media = collect_media()
    worlds = collect_worlds()
    deciding = collect_purchases_deciding()
    bought = collect_purchases_bought()

    new_text = render(media, worlds, deciding, bought)
    old_text = OUT.read_text(encoding="utf-8") if OUT.exists() else None
    if new_text == old_text:
        print("catalog: no change")
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(new_text, encoding="utf-8")
    n_media = sum(len(items) for cats in media.values() for items in cats.values())
    n_worlds = sum(len(v) for v in worlds.values())
    n_deciding = sum(len(v) for v in deciding.values())
    print(f"catalog: rewrote AIOS/generated/catalog.md -- {n_media} media, "
          f"{n_worlds} world(s), {n_deciding} purchase decision(s) in progress, "
          f"{len(bought)} logged purchase(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
