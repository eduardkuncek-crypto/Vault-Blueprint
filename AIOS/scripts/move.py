#!/usr/bin/env python3
"""
AIOS/scripts/move.py

Move or rename one file or folder in the vault, and propagate the change
everywhere it's mentioned — notes, scripts, config — in one command,
instead of hand-editing every place that named the old path.

    python3 AIOS/scripts/move.py "<old/vault/relative/path>" "<new/vault/relative/path>" --reason "why"

What it does, in order:
  1. Refuses to touch Privat/, refuses if old doesn't exist or new already does.
  2. Moves the file or folder (git mv if the tree is a git repo, else plain move).
  3. Updates the matching constant in paths.py, if the old path was registered
     there.
  4. Scans every text file in the vault (.md .py .json .txt .base) and rewrites
     two kinds of reference:
       a. Plain path strings — "AIOS/scripts/foo.py", inside backticks, quotes,
          or prose.
       b. Python path-join chains — VAULT / "AIOS" / "scripts", or
          os.path.join(VAULT, "AIOS", "scripts") — so existing scripts that
          build their own paths don't need to be pre-migrated to paths.py
          for this to work.
  5. Runs `python3 -m py_compile` on every .py file it edited, as a safety
     check — reports any that fail instead of leaving it silently broken.
  6. Logs one row to AIOS/reference/moves.md (history, never overwritten)
     and one line to today's daily note under ## Changes.
  7. Prints the numbers: files touched, occurrences replaced, anything it
     could not confidently rewrite (flagged, not guessed at).

Dry run first if unsure: --dry-run shows what would change without touching
anything.

No dependencies. Plain stdlib.
"""
import argparse
import datetime
import py_compile
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P  # noqa: E402

VAULT = P.VAULT
SKIP_DIRS = {".git", "Privat", "__pycache__", ".obsidian"}
SKIP_PATH_PARTS = {
    "AIOS/history/chat-history/cowork",
    "AIOS/history/chat-history/cowork-raw",
    "AIOS/history/scripts",
}
TEXT_SUFFIXES = {".md", ".py", ".json", ".txt", ".base"}
SKIP_FILENAMES = {".route-cache.json"}  # large machine cache, self-regenerates


def is_skipped(rel: Path) -> bool:
    parts = rel.as_posix()
    if any(part in SKIP_DIRS for part in rel.parts):
        return True
    if any(parts.startswith(skip) for skip in SKIP_PATH_PARTS):
        return True
    if rel.name in SKIP_FILENAMES:
        return True
    return False


def iter_text_files():
    # These record where things USED to be. Rewriting them to the new path
    # destroys the only trail back. moves.md and the daily notes are history.
    HISTORY_EXEMPT = ("AIOS/reference/moves.md", "Calendar/Daily/", "Calendar/Weekly/")
    for p in VAULT.rglob("*"):
        if not p.is_file() or p.suffix not in TEXT_SUFFIXES:
            continue
        rel = p.relative_to(VAULT)
        if is_skipped(rel):
            continue
        if str(p).replace(str(VAULT) + '/', '').startswith(HISTORY_EXEMPT):
            continue
        yield p


def literal_pattern(path_text: str) -> re.Pattern:
    """Match path_text as a standalone path token: not preceded or followed
    by a character that would make it part of a longer path/word, but a
    trailing '/' or filename-continuing '.' is fine to also catch."""
    esc = re.escape(path_text)
    return re.compile(r"(?<![\w./-])" + esc + r"(?![\w-])")


def replace_literal(text: str, old: str, new: str):
    count = 0
    pat = literal_pattern(old)
    text, n = pat.subn(new, text)
    count += n
    return text, count


# Deliberately intra-line only ([ \t] not \s) — \s* would cross newlines and
# let the chain eat unrelated code between two real join-expressions,
# silently swallowing whichever one falls inside the bogus multi-line span.
GB_QUOTED = r'"[^"\n]+"|\'[^\'\n]+\''  # quoted string, single line only

JOIN_CHAIN = re.compile(
    rf"""
    (?P<base>[A-Za-z_][A-Za-z0-9_.]*)                  # VAULT, ROOT, self.vault, ...
    (?P<segs>(?:[ \t]*/[ \t]*(?:{GB_QUOTED}))+)        # / "seg" / "seg" ...
    """,
    re.VERBOSE,
)
JOIN_CALL = re.compile(
    rf"""os\.path\.join\([ \t]*
    (?P<base>[A-Za-z_][A-Za-z0-9_.]*)
    (?P<segs>(?:[ \t]*,[ \t]*(?:{GB_QUOTED}))+)
    [ \t]*\)""",
    re.VERBOSE,
)


def _split_seg_string(segs_text: str, sep_pattern: str):
    parts = re.findall(GB_QUOTED, segs_text)
    return parts


def _rewrite_join(match, sep_style, old_parts, new_parts):
    segs_text = match.group("segs")
    quoted = _split_seg_string(segs_text, sep_style)
    literal_values = [q[1:-1] for q in quoted]
    n = len(old_parts)
    for start in range(0, len(literal_values) - n + 1):
        if literal_values[start:start + n] == old_parts:
            new_quoted = [f'"{v}"' for v in new_parts]
            rebuilt = quoted[:start] + new_quoted + quoted[start + n:]
            if sep_style == "/":
                new_segs = "".join(f" / {q}" for q in rebuilt)
            else:
                new_segs = "".join(f", {q}" for q in rebuilt)
            return match.group(0).replace(segs_text, new_segs, 1), True
    return match.group(0), False


def replace_python_joins(text: str, old: str, new: str):
    old_parts = old.strip("/").split("/")
    new_parts = new.strip("/").split("/")
    count = 0

    def sub_chain(m):
        nonlocal count
        rebuilt, hit = _rewrite_join(m, "/", old_parts, new_parts)
        if hit:
            count += 1
        return rebuilt

    def sub_call(m):
        nonlocal count
        rebuilt, hit = _rewrite_join(m, ",", old_parts, new_parts)
        if hit:
            count += 1
        return rebuilt

    text = JOIN_CALL.sub(sub_call, text)
    text = JOIN_CHAIN.sub(sub_chain, text)
    return text, count


def remap(p: Path, old_rel: str, new_rel: str) -> Path:
    """If p was inside the subtree that just moved, return where it lives
    now. Needed because paths.py's constants are computed once at import
    time and go stale the moment the move itself relocates the folder one
    of them lives in."""
    rel = p.relative_to(VAULT).as_posix()
    if rel == old_rel or rel.startswith(old_rel + "/"):
        return VAULT / (new_rel + rel[len(old_rel):])
    return p


def do_move(old_rel: str, new_rel: str, reason: str, dry_run: bool):
    old_rel = old_rel.strip("/")
    new_rel = new_rel.strip("/")

    for label, rel in (("old", old_rel), ("new", new_rel)):
        if ".." in Path(rel).parts:
            print(f"REFUSED: {label} path escapes the vault: {rel}")
            return 1

    old_abs = VAULT / old_rel
    new_abs = VAULT / new_rel

    if old_rel.startswith("Privat") or new_rel.startswith("Privat"):
        print("REFUSED: Privat/ is never touched.")
        return 1
    if not old_abs.exists():
        print(f"REFUSED: old path doesn't exist: {old_rel}")
        return 1
    if new_abs.exists():
        print(f"REFUSED: new path already exists: {new_rel}")
        return 1

    print(f"Moving:  {old_rel}\n     ->  {new_rel}")
    if reason:
        print(f"Reason:  {reason}")

    touched = []
    total_occurrences = 0
    compile_failures = []
    old_variants = [old_rel, old_rel + "/"] if old_abs.is_dir() else [old_rel]
    new_variants = [new_rel, new_rel + "/"] if old_abs.is_dir() else [new_rel]

    for f in iter_text_files():
        try:
            original = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        text = original
        file_hits = 0
        for ov, nv in zip(old_variants, new_variants):
            text, n = replace_literal(text, ov, nv)
            file_hits += n
        if f.suffix == ".py":
            text, n2 = replace_python_joins(text, old_rel, new_rel)
            file_hits += n2
        if text != original:
            touched.append((f.relative_to(VAULT).as_posix(), file_hits))
            total_occurrences += file_hits
            if not dry_run:
                f.write_text(text, encoding="utf-8")
                if f.suffix == ".py":
                    try:
                        py_compile.compile(str(f), doraise=True)
                    except py_compile.PyCompileError as e:
                        compile_failures.append((f.relative_to(VAULT).as_posix(), str(e)))

    if dry_run:
        print("\n--- DRY RUN, nothing written ---")
        for name, n in touched:
            print(f"  would touch {name}  ({n} occurrence(s))")
        print(f"\n{len(touched)} file(s), {total_occurrences} occurrence(s).")
        return 0

    new_abs.parent.mkdir(parents=True, exist_ok=True)
    moved_via_git = False
    if (VAULT / ".git").exists():
        r = subprocess.run(["git", "-C", str(VAULT), "mv", old_rel, new_rel],
                            capture_output=True, text=True)
        moved_via_git = r.returncode == 0
    if not moved_via_git:
        shutil.move(str(old_abs), str(new_abs))

    paths_py_now = remap(P.PATHS_PY, old_rel, new_rel)
    moves_now = remap(P.MOVES, old_rel, new_rel)

    const_name = P.find_constant(old_rel)
    paths_updated = any(name == "AIOS/scripts/paths.py" for name, _ in touched) if const_name else False
    if const_name and paths_py_now.exists():
        paths_updated = f"{const_name} = " in paths_py_now.read_text(encoding="utf-8")

    moves_now.parent.mkdir(parents=True, exist_ok=True)
    if not moves_now.exists():
        moves_now.write_text(
            "# moves.md\n\n"
            "> History of every relocation made through `move.py`. Never edited by\n"
            "> hand, never overwritten — append only. If a note or script still\n"
            "> mentions an old path, this is where to find out where it went.\n\n"
            "| Date | Old path | New path | Reason | Files touched |\n"
            "|---|---|---|---|---|\n",
            encoding="utf-8",
        )
    today = datetime.date.today().isoformat()
    row = f"| {today} | `{old_rel}` | `{new_rel}` | {reason or '—'} | {len(touched)} |\n"
    with moves_now.open("a", encoding="utf-8") as fh:
        fh.write(row)

    daily = P.daily_note(today) if hasattr(P, "daily_note") else None
    if daily:
        changelog_line = (
            f"- {datetime.datetime.now().strftime('%H:%M')} moved `{old_rel}` -> "
            f"`{new_rel}` ({len(touched)} file(s) updated) — see moves.md\n"
        )
        if daily.exists():
            content = daily.read_text(encoding="utf-8")
            if "## Changes" in content:
                content = content.replace("## Changes\n", "## Changes\n" + changelog_line, 1)
            else:
                content += "\n## Changes\n" + changelog_line
            daily.write_text(content, encoding="utf-8")

    exempt = {moves_now.relative_to(VAULT).as_posix()}
    leftover = []
    for f in iter_text_files():
        rel = f.relative_to(VAULT).as_posix()
        if rel in exempt or rel.startswith("Calendar/Daily/"):
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if literal_pattern(old_rel).search(text):
            leftover.append(rel)

    print(f"\nMoved via {'git mv' if moved_via_git else 'plain move'}.")
    if const_name:
        print(f"paths.py constant {const_name} updated: {paths_updated}")
    print(f"{len(touched)} file(s) updated, {total_occurrences} occurrence(s) rewritten:")
    for name, n in touched:
        print(f"  {name}  ({n})")
    if compile_failures:
        print("\nWARNING — these .py files no longer compile after the rewrite:")
        for name, err in compile_failures:
            print(f"  {name}: {err}")
    else:
        print("All touched .py files still compile.")
    if leftover:
        print(f"\nWARNING — {len(leftover)} file(s) still mention `{old_rel}`, check by hand:")
        for name in leftover:
            print(f"  {name}")
    else:
        print("No remaining mentions of the old path anywhere in the vault.")
    print(f"\nHistory row added to {moves_now.relative_to(VAULT).as_posix()}")
    print("Privat/ touched: no")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("old_path")
    ap.add_argument("new_path")
    ap.add_argument("--reason", default="")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    sys.exit(do_move(args.old_path, args.new_path, args.reason, args.dry_run))


if __name__ == "__main__":
    main()
