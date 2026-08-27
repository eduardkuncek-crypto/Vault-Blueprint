#!/usr/bin/env python3
"""
migration-scan.py — rebuild the generated inventory block inside AIOS/reference/migration.md.

Why this exists
----------------
`AIOS/reference/migration.md` is the file you hand to a *different* AI when
you switch providers. Most of that file is judgement — how to reconstruct
trigger-based behaviour in a system that isn't Claude/Cowork — and a script
can't write judgement. But the raw facts underneath the judgement (which
skills exist, which routines are on a schedule and therefore break on a
provider switch, which scripts are plain stdlib and therefore travel for
free) ARE mechanical. Those go in a GENERATED block so they can't drift from
what's actually installed, same pattern as `vault-map.py`'s Scale block.

Nothing calls this automatically. Migration prep isn't continuous, so
there's no event to hang an automatic re-run on — it happens on request
("make vault migratable"), and the `migrate` routine runs this script as its
first step, every time, so the block is never stale when it actually gets
read.

Usage
-----
    python3 AIOS/scripts/migration-scan.py            # print the inventory, change nothing
    python3 AIOS/scripts/migration-scan.py --write     # rewrite the block in migration.md
"""
import re
import sys
import pathlib
from datetime import date

ROOT = pathlib.Path(__file__).resolve().parents[2]
SKILL_MAP = ROOT / "AIOS" / "skill-map.md"
SKILLS_DIR = ROOT / "AIOS" / "skills"
SCRIPTS_DIR = ROOT / "AIOS" / "scripts"
MIGRATION = ROOT / "AIOS" / "reference" / "migration.md"

BEGIN = "<!-- BEGIN GENERATED: inventory -->"
END = "<!-- END GENERATED: inventory -->"

SCHEDULE_PATTERN = re.compile(
    r"\(scheduled\)|cron|\btimer\b|\bhourly\b|every \d+ min|\d{1,2}:\d{2}",
    re.I,
)


def parse_installed_skills():
    """Every `skill-name` in a table row before the '## Routines' heading."""
    text = SKILL_MAP.read_text(encoding="utf-8")
    installed_section = text.split("## Routines", 1)[0]
    names = re.findall(r"^\|\s*`([a-zA-Z0-9\-]+)`\s*\|", installed_section, re.M)
    seen = []
    for n in names:
        if n not in seen:
            seen.append(n)
    return seen


def parse_routines():
    """Rows of the Routines table: (name, fires, oneline)."""
    text = SKILL_MAP.read_text(encoding="utf-8")
    if "## Routines" not in text:
        return []
    section = text.split("## Routines", 1)[1]
    section = section.split("## Adding a routine", 1)[0]
    rows = []
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith("|") or line.startswith("|---"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 3:
            continue
        name = cells[0].strip("` ")
        if name.lower() in ("routine",):
            continue
        rows.append((name, cells[1], cells[2]))
    return rows


def mirrored_skill_dirs():
    if not SKILLS_DIR.exists():
        return []
    return sorted(p.name for p in SKILLS_DIR.iterdir() if p.is_dir())


def scripts_list():
    return sorted(p.name for p in SCRIPTS_DIR.glob("*.py") if not p.name.startswith("_"))


def build_block():
    installed = parse_installed_skills()
    routines = parse_routines()
    mirrored = mirrored_skill_dirs()
    scripts = scripts_list()

    scheduled = [(n, f) for (n, f, _) in routines if SCHEDULE_PATTERN.search(f)]
    on_request = [(n, f) for (n, f, _) in routines if not SCHEDULE_PATTERN.search(f)]

    lines = [BEGIN, "", f"**Rebuilt {date.today().isoformat()} by `migration-scan.py`.**", ""]

    lines.append("### Skills declared in skill-map.md (%d)" % len(installed))
    lines.append("")
    lines.append(", ".join(f"`{n}`" for n in installed) if installed else "*(none found)*")
    lines.append("")

    lines.append("### Skills actually mirrored to AIOS/skills/ as plain SKILL.md (%d)" % len(mirrored))
    lines.append("")
    lines.append(", ".join(f"`{n}`" for n in mirrored) if mirrored else "*(none found)*")
    missing = sorted(set(installed) - set(mirrored))
    if missing:
        lines.append("")
        lines.append(f"**Declared but not mirrored — {', '.join('`'+m+'`' for m in missing)}. These will NOT travel with the vault; a new AI gets nothing for them except this list.**")
    lines.append("")

    lines.append("### Routines that fire on a schedule — break on provider switch (%d)" % len(scheduled))
    lines.append("")
    if scheduled:
        for n, f in scheduled:
            lines.append(f"- `{n}` — fires: {f}")
    else:
        lines.append("*(none found)*")
    lines.append("")

    lines.append("### Routines that fire on request or on a trigger phrase — logic is portable, the *automatic firing* isn't (%d)" % len(on_request))
    lines.append("")
    if on_request:
        for n, f in on_request:
            lines.append(f"- `{n}` — fires: {f}")
    else:
        lines.append("*(none found)*")
    lines.append("")

    lines.append("### Scripts in AIOS/scripts/ — plain stdlib Python, no provider dependency (%d)" % len(scripts))
    lines.append("")
    lines.append(", ".join(f"`{s}`" for s in scripts) if scripts else "*(none found)*")
    lines.append("")

    lines.append(END)
    return "\n".join(lines)


def main():
    block = build_block()
    if "--write" in sys.argv:
        if not MIGRATION.exists():
            print("migration-scan: AIOS/reference/migration.md doesn't exist yet — create it first, then run --write.", file=sys.stderr)
            sys.exit(1)
        text = MIGRATION.read_text(encoding="utf-8")
        if BEGIN not in text or END not in text:
            print("migration-scan: migration.md has no GENERATED markers to replace.", file=sys.stderr)
            sys.exit(1)
        new_text = re.sub(
            re.escape(BEGIN) + r".*?" + re.escape(END),
            block,
            text,
            flags=re.S,
        )
        MIGRATION.write_text(new_text, encoding="utf-8")
        print(f"migration-scan: rewrote inventory block in {MIGRATION}")
    else:
        print(block)


if __name__ == "__main__":
    main()
