#!/usr/bin/env python3
"""
AIOS/scripts/event.py

Dated things that are not projects and not diary entries: a trip, a holiday,
a concert, an exam week, an appointment, a visit. They live in
`Calendar/Events/YYYY/<Title>.md` and they connect themselves to the days
they cover.

    python3 AIOS/scripts/event.py "Croatia Trip" --start 2026-08-21 \
        --end 2026-08-30 --where "Mljet, Croatia" --tag travel \
        --about "Family holiday, driving down."

    python3 AIOS/scripts/event.py --sync        # reconnect + refresh statuses
    python3 AIOS/scripts/event.py --today       # what's on today
    python3 AIOS/scripts/event.py --upcoming 14 # the next two weeks
    python3 AIOS/scripts/event.py --list        # everything, newest first

WHY THIS EXISTS: a note about a trip that just sits in a folder, with nothing
on the days it actually covers pointing at it, is a note that won't be read
on the day it matters.

The connection is a mechanism, not a rule:

  * `--sync` rebuilds an `## Events` section in every daily note the event
    covers, and it is idempotent — running it twice changes nothing.
  * `logchange.py` runs `--sync` automatically whenever anything under
    `Calendar/Events/` is written, so an event connects itself the moment it
    is created, and again whenever its dates change.
  * `status:` is derived from today's date on every sync — upcoming ->
    happening -> done — so no event silently sits in the wrong tense.
    `cancelled` is the one status a human sets and a sync never overwrites.

No dependencies. Plain stdlib.
"""

import argparse
import datetime as dt
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P  # noqa: E402

VAULT = P.VAULT
EVENTS = P.EVENTS
TEMPLATE = VAULT / "AIOS" / "templates" / "event-note.md"
DAILY_TEMPLATE = VAULT / "AIOS" / "templates" / "daily-note.md"
LOGCHANGE = VAULT / "AIOS" / "scripts" / "logchange.py"

EVENTS_HEADING = "## Events"
EVENTS_BLURB = (
    "%% Machine-written by `AIOS/scripts/event.py`. Every event note whose dates "
    "cover this day, linked. Rebuilt on every sync — don't hand-edit, edit the "
    "event note instead. %%"
)
STATUSES = ("upcoming", "happening", "done", "cancelled")

# How far back --sync is willing to create a missing daily note. An event
# that started in March shouldn't conjure ninety empty notes.
BACKFILL_DAYS = 45


# ---------------------------------------------------------------- frontmatter

def split_front(text: str):
    """Return (frontmatter_dict, whole_text). Values stay strings."""
    fm = {}
    if not text.startswith("---"):
        return fm, text
    end = text.find("\n---", 3)
    if end == -1:
        return fm, text
    for line in text[3:end].splitlines():
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m:
            fm[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return fm, text


def set_front(text: str, key: str, value: str) -> str:
    """Set one frontmatter key, preserving everything else."""
    if not text.startswith("---"):
        return text
    end = text.find("\n---", 3)
    if end == -1:
        return text
    head, rest = text[:end], text[end:]
    pat = re.compile(rf"^({re.escape(key)}):.*$", re.M)
    if pat.search(head):
        return pat.sub(rf"\1: {value}", head, count=1) + rest
    return head.rstrip("\n") + f"\n{key}: {value}" + rest


BAD_TITLE = re.compile(r'[\\/:*?"<>|\[\]]|^\.|\.\.')


def clean_title(title: str) -> str:
    """A title becomes both a filename and a wikilink, so it can't contain
    a slash, `[]`, a quote, or `..`. Rejected loudly rather than mangled — a
    renamed event is worse than an error."""
    t = title.strip()
    if not t or BAD_TITLE.search(t):
        raise ValueError(
            f"bad event title {title!r} — no / \\ : * ? \" < > | [ ] and no "
            f"leading dot or '..'. It becomes a filename and a wikilink.")
    return t


def as_date(s):
    if not s:
        return None
    try:
        return dt.date.fromisoformat(str(s).strip())
    except ValueError:
        return None


# ---------------------------------------------------------------- model

class Event:
    def __init__(self, path: Path):
        self.path = path
        self.text = path.read_text(encoding="utf-8")
        fm, _ = split_front(self.text)
        self.title = fm.get("title") or path.stem
        self.start = as_date(fm.get("start"))
        self.end = as_date(fm.get("end"))
        # A blank `end:` means open-ended — it's running and nobody has
        # written down when it stops. It covers start..today until an end is
        # filled in. A genuinely one-day thing gets `end:` equal to `start:`.
        self.open_ended = self.end is None
        self.where = fm.get("where", "")
        self.status = (fm.get("status") or "").lower()

    @property
    def valid(self) -> bool:
        return self.start is not None

    @property
    def broken(self) -> str:
        """Why this event can't be trusted, or '' if it's fine."""
        if self.start is None:
            return "no usable `start:` date (needs YYYY-MM-DD)"
        if self.end and self.end < self.start:
            return f"`end:` {self.end} is before `start:` {self.start}"
        return ""

    def last_day(self, today: dt.date) -> dt.date:
        if self.end:
            return self.end
        return max(self.start, today) if self.open_ended else self.start

    def covers(self, d: dt.date, today: dt.date | None = None) -> bool:
        today = today or dt.date.today()
        return bool(self.start and self.start <= d <= self.last_day(today))

    def days(self, today: dt.date | None = None) -> int:
        today = today or dt.date.today()
        return (self.last_day(today) - self.start).days + 1

    def derived_status(self, today: dt.date) -> str:
        if self.status == "cancelled":
            return "cancelled"
        if today < self.start:
            return "upcoming"
        if self.covers(today, today):
            return "happening"
        return "done"

    def label_for(self, d: dt.date, today: dt.date | None = None) -> str:
        """The bit after the wikilink in a daily note."""
        today = today or dt.date.today()
        n = (d - self.start).days + 1
        total = self.days(today)
        bits = []
        if self.open_ended:
            bits.append("starts" if n == 1 else f"day {n}")
        elif total == 1:
            bits.append("all day")
        elif d == self.start:
            bits.append(f"day 1 of {total} — starts")
        elif d == self.end:
            bits.append(f"day {total} of {total} — last day")
        else:
            bits.append(f"day {n} of {total}")
        if self.where:
            bits.append(self.where)
        return " · ".join(b for b in bits if b)


def load_events(loud=True) -> list:
    """Every usable event. A note that can't be used is REPORTED, never
    silently skipped."""
    out = []
    for p in sorted(EVENTS.rglob("*.md")) if EVENTS.exists() else []:
        if p.stem == "Events":
            continue
        e = Event(p)
        why = e.broken
        if why:
            if loud:
                print(f"event: IGNORING {P.relative(p)} — {why}",
                      file=sys.stderr)
            continue
        out.append(e)
    return sorted(out, key=lambda e: e.start)


# ---------------------------------------------------------------- daily notes

def daily_text_with_events(text: str, lines: list) -> str:
    """Return text with the `## Events` section replaced by `lines`
    (or removed entirely when `lines` is empty)."""
    block = ""
    if lines:
        block = (f"{EVENTS_HEADING}\n\n{EVENTS_BLURB}\n\n"
                 + "\n".join(lines) + "\n\n")

    existing = re.search(rf"^{re.escape(EVENTS_HEADING)}\s*$", text, re.M)
    if existing:
        rest = text[existing.end():]
        nxt = re.search(r"^(## |---\s*$)", rest, re.M)
        cut = existing.end() + (nxt.start() if nxt else len(rest))
        return text[:existing.start()] + block + text[cut:]

    if not lines:
        return text

    # Insert before `## Diary` — after the Brief, before what happened.
    diary = re.search(r"^## Diary\s*$", text, re.M)
    if diary:
        return text[:diary.start()] + block + text[diary.start():]
    changes = re.search(r"^## Changes\s*$", text, re.M)
    if changes:
        return text[:changes.start()] + block + text[changes.start():]
    return text.rstrip("\n") + "\n\n" + block


def render_daily_template(d: dt.date) -> str:
    if DAILY_TEMPLATE.exists():
        t = DAILY_TEMPLATE.read_text(encoding="utf-8")
        t = t.replace("{{date:YYYY-MM-DD}}", d.isoformat())
        t = t.replace("{{date:dddd, D MMMM YYYY}}",
                      f"{d:%A}, {d.day} {d:%B} {d:%Y}")
        return t
    return (f"---\ntitle: \"{d.isoformat()}\"\ndate: {d.isoformat()}\n"
            f"tags:\n  - daily\n---\n\n# {d:%A}, {d.day} {d:%B} {d:%Y}\n\n"
            "## Brief\n\n## Diary\n\n## Changes\n")


def log(what: str, where: str, kind: str = "edit") -> None:
    """One receipt line, with the recursion guard set so logchange doesn't
    call this script straight back."""
    if not LOGCHANGE.exists():
        return
    env = dict(os.environ, AIOS_EVENT_SYNC="1")
    subprocess.run([sys.executable or "python3", str(LOGCHANGE), what, where,
                    "--kind", kind],
                   capture_output=True, text=True, timeout=60, env=env)


# ---------------------------------------------------------------- commands

def cmd_sync(today: dt.date, quiet=False, dry=False) -> int:
    events = load_events()
    if not events:
        if not quiet:
            print("event: no event notes yet.")
        return 0

    touched, created, restatused = [], [], []

    for e in events:
        want = e.derived_status(today)
        if e.status != want:
            if not dry:
                e.path.write_text(set_front(e.text, "status", want),
                                  encoding="utf-8")
                e.text = e.path.read_text(encoding="utf-8")
            restatused.append(f"{e.title}: {e.status or '(none)'} -> {want}")
            e.status = want

    wanted: dict = {}
    for e in events:
        d = e.start
        while d <= e.last_day(today):
            wanted.setdefault(d, []).append(e)
            d += dt.timedelta(days=1)

    days = set(wanted)
    for p in P.all_daily_notes():
        try:
            days.add(dt.date.fromisoformat(p.stem))
        except ValueError:
            continue

    for d in sorted(days):
        covering = wanted.get(d, [])
        path = P.find_daily_note(d)
        if path is None:
            if not covering or d > today or (today - d).days > BACKFILL_DAYS:
                continue
            path = P.daily_note(d)
            if not dry:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(render_daily_template(d), encoding="utf-8")
            created.append(P.relative(path))

        text = path.read_text(encoding="utf-8") if path.exists() else \
            render_daily_template(d)
        lines = [f"- [[{e.title}]] — {e.label_for(d, today)}" for e in covering]
        new = daily_text_with_events(text, lines)
        if new != text:
            if not dry:
                path.write_text(new, encoding="utf-8")
            touched.append(P.relative(path))

    if not quiet:
        print(f"event sync: {len(events)} events · "
              f"{len(touched)} daily notes connected · "
              f"{len(created)} created · {len(restatused)} statuses refreshed")
        for r in restatused:
            print(f"  status  {r}")
        for t in touched:
            print(f"  linked  {t}")
    if not dry and touched:
        log(f"Events connected to {len(touched)} daily note(s) "
            f"({', '.join(e.title for e in events if e.covers(today, today)) or 'no event today'})",
            "Calendar/Daily/", "edit")
    return 0


def cmd_new(args, today: dt.date) -> int:
    start = as_date(args.start)
    if not start:
        print("event: --start YYYY-MM-DD is required", file=sys.stderr)
        return 1
    end = None if args.open else (as_date(args.end) or start)
    if end and end < start:
        print("event: --end is before --start", file=sys.stderr)
        return 1

    try:
        title = clean_title(args.title)
    except ValueError as exc:
        print(f"event: {exc}", file=sys.stderr)
        return 1
    args.title = title
    path = P.event_note(title, start)
    if path.exists():
        print(f"event: already exists — {P.relative(path)}", file=sys.stderr)
        return 1

    tags = ["event"] + [t for t in (args.tag or []) if t != "event"]
    status = (args.status or "").lower()
    if status and status not in STATUSES:
        print(f"event: status must be one of {STATUSES}", file=sys.stderr)
        return 1
    if not status:
        last = end or max(start, today)
        status = ("upcoming" if today < start else
                  "happening" if start <= today <= last else "done")

    body = TEMPLATE.read_text(encoding="utf-8") if TEMPLATE.exists() else (
        "---\ntitle: \"{{title}}\"\ntags:\n  - event\nstart: {{start}}\n"
        "end: {{end}}\nwhere: \"{{where}}\"\nstatus: {{status}}\n---\n\n"
        "# {{title}}\n\n{{about}}\n")
    body = (body
            .replace("{{title}}", args.title)
            .replace("{{start}}", start.isoformat())
            .replace("{{end}}", end.isoformat() if end else "")
            .replace("{{where}}", args.where or "")
            .replace("{{status}}", status)
            .replace("{{about}}", args.about or "_One line on what this is._"))
    body = body.replace("tags:\n  - event\n",
                        "tags:\n" + "".join(f"  - {t}\n" for t in tags))

    if args.dry_run:
        print(f"event: would create {P.relative(path)}")
        print(body)
        return 0

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    print(f"event: created {P.relative(path)}")
    log(f"Event: {args.title} ({start}"
        f"{' → ' + end.isoformat() if end and end != start else ' → open' if not end else ''}"
        f"{', ' + args.where if args.where else ''})",
        P.relative(path), "new")
    return cmd_sync(today, quiet=False)


def cmd_report(today: dt.date, mode: str, window: int) -> int:
    events = load_events()
    if mode == "today":
        hits = [e for e in events if e.covers(today, today)]
        if not hits:
            print("Nothing on today.")
            return 0
        for e in hits:
            print(f"{e.title} — {e.label_for(today, today)}  "
                  f"[{e.derived_status(today)}]")
        return 0

    if mode == "upcoming":
        edge = today + dt.timedelta(days=window)
        hits = [e for e in events
                if today <= e.start <= edge or e.covers(today, today)]
        if not hits:
            print(f"Nothing in the next {window} days.")
            return 0
        for e in hits:
            when = "today" if e.start == today else \
                f"in {(e.start - today).days} days" if e.start > today else \
                f"day {(today - e.start).days + 1} of {e.days(today)}"
            print(f"{e.start}  {e.title:<32} {when:<14} "
                  f"{e.where}  [{e.derived_status(today)}]")
        return 0

    for e in reversed(events):
        span = e.start.isoformat() + (f" → {e.end}" if e.end and e.end != e.start
                                      else " → (open)" if e.open_ended else "")
        print(f"{span:<26} {e.title:<32} [{e.derived_status(today)}] "
              f"{e.where}  {P.relative(e.path)}")
    if not events:
        print("No events yet.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("title", nargs="?", help="event title, e.g. 'Croatia Trip'")
    ap.add_argument("--start", help="YYYY-MM-DD")
    ap.add_argument("--end", help="YYYY-MM-DD (omit for a single-day event)")
    ap.add_argument("--open", action="store_true",
                    help="open-ended: running, end date not known yet")
    ap.add_argument("--where", help="place, e.g. 'Mljet, Croatia'")
    ap.add_argument("--about", help="one line on what it is")
    ap.add_argument("--tag", action="append", help="extra tag, repeatable")
    ap.add_argument("--status", help=f"one of {STATUSES}; derived if omitted")
    ap.add_argument("--sync", action="store_true",
                    help="reconnect every event to its days, refresh statuses")
    ap.add_argument("--today", action="store_true", help="what's on today")
    ap.add_argument("--upcoming", type=int, nargs="?", const=14,
                    help="events starting in the next N days (default 14)")
    ap.add_argument("--list", action="store_true", help="every event")
    ap.add_argument("--date", help="pretend today is YYYY-MM-DD (testing)")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    today = as_date(args.date) or dt.date.today()
    EVENTS.mkdir(parents=True, exist_ok=True)

    if args.sync:
        return cmd_sync(today, quiet=args.quiet, dry=args.dry_run)
    if args.today:
        return cmd_report(today, "today", 0)
    if args.upcoming is not None:
        return cmd_report(today, "upcoming", args.upcoming)
    if args.list:
        return cmd_report(today, "list", 0)
    if args.title:
        return cmd_new(args, today)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
