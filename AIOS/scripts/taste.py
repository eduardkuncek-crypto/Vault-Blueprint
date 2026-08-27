#!/usr/bin/env python3
"""
taste.py -- compile every "## Taste" section in the vault into one fast-read
profile at AIOS/generated/taste.md.

Why: figuring out someone's taste in a specific category by grepping four
scattered notes costs real time. The fix is a convention plus one script,
not a rule to remember.

Convention: any note can carry a `## Taste` section -- a short, dense list of
concrete likes/dislikes/pet-peeves for that subject. This script does no
judgement, only extraction: it walks the vault, pulls every `## Taste`
section verbatim, groups it by category, and writes the compiled result to
AIOS/generated/taste.md. The facts still live in their subject notes -- this
is an index, same shape as where.md and commands.md.

Category comes from (in order):
  1. frontmatter tags, for Atlas/Media/ notes (anime/manga/game/show/film/book)
  2. the note's parent folder name, as a fallback

Regenerated automatically by logchange.py's refresh_taste_profile() guard,
which fires whenever a write touches a file that actually has a ## Taste
section -- no hardcoded file list to maintain, any note that grows one gets
picked up on its next write. Can also be run by hand:
    python3 AIOS/scripts/taste.py

No dependencies. Plain stdlib.
"""
import datetime as dt
import re
import sys
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent.parent
OUT = VAULT / "AIOS" / "generated" / "taste.md"

SKIP_DIRS = {"Privat", ".git", ".obsidian", ".trash", "history", "skills"}

TAG_CATEGORY = {
    "anime": "Anime & Manga",
    "manga": "Anime & Manga",
    "game": "Games",
    "show": "Shows & Films",
    "film": "Shows & Films",
    "book": "Books",
}

TASTE_RE = re.compile(r"^## Taste\s*$", re.MULTILINE)
HEADING_RE = re.compile(r"^#{1,2} ", re.MULTILINE)
TAGS_RE = re.compile(r"^tags:\s*\n((?:\s*-\s*.+\n)+)", re.MULTILINE)


def rel(p: Path) -> str:
    return str(p.relative_to(VAULT)).replace("\\", "/")


def frontmatter_tags(text: str) -> list[str]:
    m = TAGS_RE.search(text)
    if not m:
        return []
    return [ln.strip("- ").strip() for ln in m.group(1).splitlines() if ln.strip()]


def category_for(path: Path, text: str) -> str:
    r = rel(path)
    if r.startswith("Atlas/Media/"):
        for tag in frontmatter_tags(text):
            if tag in TAG_CATEGORY:
                return TAG_CATEGORY[tag]
        return "Media (other)"
    return path.parent.name or "Other"


def extract_taste(text: str) -> str | None:
    m = TASTE_RE.search(text)
    if not m:
        return None
    rest = text[m.end():]
    nxt = HEADING_RE.search(rest)
    body = rest[: nxt.start() if nxt else len(rest)]
    return body.strip("\n")


def collect() -> dict[str, list[tuple[str, str]]]:
    groups: dict[str, list[tuple[str, str]]] = {}
    for md in sorted(VAULT.rglob("*.md")):
        parts = rel(md).split("/")
        if any(part in SKIP_DIRS for part in parts):
            continue
        try:
            text = md.read_text(encoding="utf-8")
        except OSError as e:
            print(f"taste: skipped {md} ({e})", file=sys.stderr)
            continue
        body = extract_taste(text)
        if not body:
            continue
        cat = category_for(md, text)
        groups.setdefault(cat, []).append((md.stem, body))
    return groups


def render(groups: dict[str, list[tuple[str, str]]]) -> str:
    now = dt.datetime.now()
    lines = [
        "---",
        "title: taste",
        "tags:",
        "  - generated",
        "---",
        "",
        "# Taste profile",
        "",
        "> [!info] This file is generated -- do not edit it by hand",
        "> Compiled from every `## Taste` section in the vault by "
        "`python3 AIOS/scripts/taste.py`. Add taste facts to the subject "
        "note's own `## Taste` heading, not here -- this only collects them. "
        f"Rebuilt {now:%Y-%m-%d %H:%M}.",
        "",
    ]
    for cat in sorted(groups):
        lines.append(f"## {cat}")
        lines.append("")
        for title, body in groups[cat]:
            lines.append(f"**{title}**")
            lines.append(body)
            lines.append("")
    if not groups:
        lines.append("*Nothing tagged yet -- add a `## Taste` section to a note.*")
    return "\n".join(lines).rstrip("\n") + "\n"


def main() -> None:
    groups = collect()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    new_text = render(groups)
    old_text = OUT.read_text(encoding="utf-8") if OUT.exists() else None
    if new_text == old_text:
        print("taste: no change")
        return
    OUT.write_text(new_text, encoding="utf-8")
    n = sum(len(v) for v in groups.values())
    print(f"taste: rewrote AIOS/generated/taste.md -- {n} taste section(s) "
          f"across {len(groups)} categor(y/ies)")


if __name__ == "__main__":
    main()
