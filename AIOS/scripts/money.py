#!/usr/bin/env python3
"""
money.py — one command to log money in/out or reconcile a real balance, so
`Atlas/About Me/Money.md` never goes stale.

WHY THIS EXISTS: a balance that only ever gets stated out loud, mid-
conversation, is a balance that isn't recorded anywhere until someone asks
for it directly. A note field ("wants to start tracking spending") is not a
mechanism; this is the mechanism.

TWO THINGS THIS SCRIPT KEEPS TRUE, AUTOMATICALLY:

  1. `## Ledger` in Money.md — an append-only table, one row per logged
     transaction or balance check, each row carrying the running balance so
     the file is self-auditing: sum the deltas, it should equal the last
     balance column.
  2. The `Current balance` row in the `## Right now` table — always the
     latest ledger balance, dated, never hand-edited out of sync with the
     ledger below it.

TWO WAYS TO USE IT:

  # Log a transaction — spend is negative, income/gift is positive
  python3 AIOS/scripts/money.py "New headphones" -89.99
  python3 AIOS/scripts/money.py "Birthday money" 50

  # Reconcile against a real balance you just checked (bank app, cash count)
  python3 AIOS/scripts/money.py --set-balance 1230 --note "bank + cash, counted"

`--set-balance` is the important one for how people actually report money:
not every transaction gets logged individually, but a stated total shows up
sooner or later. Each one is a calibration point — the script computes the
drift against what the ledger predicted (prior balance + logged transactions
since), so a growing gap between "predicted" and "actual" becomes visible
instead of silently wrong.

Maintenance:
  python3 AIOS/scripts/money.py --list --last 10
  python3 AIOS/scripts/money.py --dry-run "..." -20

Exits non-zero and prints to stderr on any failure — same contract as every
other script in AIOS/scripts/. No dependencies. Plain stdlib.

DESIGN NOTES, from adversarial testing against a sandboxed copy of a vault
built on this design (never the live vault):

  1. TOCTOU balance race. An early version read the prior balance BEFORE
     acquiring the lock, then handed a pre-computed new_balance into the
     locked write. Two `money.py` calls firing at once (plausible in an
     agentic workflow, e.g. a subagent batch) both read the same stale prior
     and computed conflicting balances — the lock stopped the write from
     being TORN, but did nothing to stop it being WRONG. Fixed by moving the
     read-prior + compute-new-balance step to INSIDE the locked critical
     section in add_row(), so it always works off a fresh read.
  2. A literal `|` in `what` or `--note` split the markdown row into extra
     cells, and the next call's cells[4] lookup then silently read the wrong
     cell as the balance — a stray `|` corrupted every balance computed
     afterward, with no error at any point. Fixed: `|` is replaced with `¦`
     (U+00A6 BROKEN BAR, visually near-identical) in both fields before a
     row is ever built, so the byte the table parser splits on can never
     appear inside a cell's content.
  3. Negative balances round-tripped wrong: fmt_balance rendered "€-50.00"
     but the parsing regex expected the sign before the €, so a negative
     balance was silently read back as positive and every later transaction
     compounded the error. Fixed: fmt_balance now matches fmt_amount's
     "-€50.00" convention, and the parser captures the sign explicitly
     instead of discarding it.
  4. A second, independent verification pass found fix #2 was incomplete:
     `--date` was never run through safe_cell and could still inject a `|`
     into the row, reproducing the exact same silent balance corruption.
     Fixed by validating --date strictly as YYYY-MM-DD (dt.date.fromisoformat)
     instead of accepting it as free text — a malformed date is refused
     outright rather than sanitized, since there's no legitimate reason for
     it to contain anything else.
"""
import scriptlog  # noqa: F401 -- logs this run to AIOS/history/scripts/

# aios-run: agent  (whenever a real balance, spend, or gift comes up)

import argparse
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P  # noqa: E402
from notelock import locked, write_atomic  # noqa: E402 -- one lock, shared with diary.py/logchange.py

VAULT = P.VAULT
NOTE_PATH = P.ABOUT_ME / "Money.md"

RIGHT_NOW_HEADING = "## Right now"
LEDGER_HEADING = "## Ledger"
LEDGER_INTRO = (
    "%% Append-only, via `AIOS/scripts/money.py`. Balance column is the "
    "running total after that row. A **Balance check** row is you stating a "
    "real number (bank app, cash count) — the Notes column shows the drift "
    "against what the ledger predicted, so a gap between predicted and "
    "actual becomes visible instead of silently wrong. Never hand-edit — "
    "the `Current balance` row above is derived from the last row here. %%"
)
LEDGER_COLS = "| Date | What | Amount | Balance | Notes |"
LEDGER_SEP = "|---|---|---|---|---|"

PIPE_SUB = "¦"  # U+00A6 BROKEN BAR — stands in for a literal "|" in free text
                 # so it can never be mistaken for a markdown table separator.


def fail(msg: str) -> None:
    print(f"money: ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def safe_cell(text: str) -> str:
    """Make free text safe to sit inside one markdown table cell. A literal
    '|' would silently add a column and shift every cell after it — see the
    design notes at the top of this file for what that did in practice. Also
    flattens newlines, which would break the row onto multiple lines."""
    if text is None:
        return ""
    flat = " ".join(str(text).replace("\r", "\n").split("\n"))
    return flat.replace("|", PIPE_SUB).strip()


def fmt_amount(n: float) -> str:
    sign = "+" if n >= 0 else "-"
    return f"{sign}€{abs(n):.2f}"


def fmt_balance(n: float) -> str:
    # Same signed convention as fmt_amount ("-€50.00", never "€-50.00") —
    # the parser below depends on this exact shape.
    sign = "-" if n < 0 else ""
    return f"{sign}€{abs(n):.2f}"


# --------------------------------------------------------------------------
# reading
# --------------------------------------------------------------------------

def find_section(lines: list[str], heading: str):
    """Return (start_idx, end_idx) of a `## Heading` section's body — the
    lines strictly between the heading and the next `## ` heading or EOF."""
    start = next((i for i, l in enumerate(lines) if l.strip() == heading), None)
    if start is None:
        return None, None
    end = next(
        (i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")),
        len(lines),
    )
    return start, end


def find_ledger_table(lines: list[str]):
    """(header_idx, last_row_idx) for the Ledger table, or (None, None) if
    the section/table doesn't exist yet."""
    start, end = find_section(lines, LEDGER_HEADING)
    if start is None:
        return None, None
    header_idx = next(
        (i for i in range(start, end) if lines[i].startswith("| Date")), None
    )
    if header_idx is None:
        return None, None
    last_row = header_idx + 1  # the |---|---| separator
    i = last_row + 1
    while i < end and lines[i].startswith("|"):
        last_row = i
        i += 1
    return header_idx, last_row


def last_ledger_balance(lines: list[str]):
    """The running balance after the most recent ledger row, or None if the
    ledger is empty/missing. Parses the Balance column (4th cell).

    Sign is captured explicitly — `fmt_balance` always puts a bare '-'
    immediately before the '€' for a negative balance, never after it, and
    this regex has to agree with that exactly or a negative balance silently
    reads back as positive (see design notes at the top of this file)."""
    header_idx, last_row_idx = find_ledger_table(lines)
    if header_idx is None or last_row_idx <= header_idx + 1:
        return None
    row = lines[last_row_idx]
    cells = [c.strip() for c in row.split("|")]
    if len(cells) < 5:
        return None
    m = re.search(r"(-)?\s*€?\s*([\d,]+\.?\d*)", cells[4])
    if not m:
        return None
    value = float(m.group(2).replace(",", ""))
    if m.group(1):
        value = -value
    return value


# --------------------------------------------------------------------------
# writing
# --------------------------------------------------------------------------

def ensure_ledger_section(lines: list[str]) -> int:
    """Return the index of the `## Ledger` heading, creating the section
    (heading + intro + empty table) right after `## Right now` if absent."""
    for i, l in enumerate(lines):
        if l.strip() == LEDGER_HEADING:
            return i

    start, end = find_section(lines, RIGHT_NOW_HEADING)
    block = [
        "", LEDGER_HEADING, "", LEDGER_INTRO, "", LEDGER_COLS, LEDGER_SEP, "",
    ]
    if start is None:
        # No Right now section either — append at the end of the file,
        # before ## Related if present, else at EOF.
        rel = next((i for i, l in enumerate(lines) if l.strip() == "## Related"), len(lines))
        lines[rel:rel] = block
        return rel + 1
    lines[end:end] = block
    return end + 1


def update_current_balance(lines: list[str], balance: float, date_str: str, source: str) -> None:
    """Set the `Current balance` row in `## Right now` to the latest ledger
    balance. Inserts the row (after the last existing row, or at the table's
    end) if it doesn't exist yet."""
    start, end = find_section(lines, RIGHT_NOW_HEADING)
    text = (
        f"| Current balance | **~{fmt_balance(balance)}** — updated {date_str} "
        f"via `money.py` ({source}) |"
    )
    if start is None:
        return  # nothing sane to do without a Right now table; ledger still wrote
    for i in range(start, end):
        if lines[i].strip().lower().startswith("| current balance"):
            lines[i] = text
            return
    # Insert after the last `| ... | ... |` row in the table, before the
    # section ends.
    last_row = None
    for i in range(start, end):
        if lines[i].startswith("|"):
            last_row = i
    if last_row is not None:
        lines.insert(last_row + 1, text)


def build_note(user_note: str, prior) -> str:
    """The Notes-column text for a --set-balance row: the raw note plus a
    drift line computed against whatever the ledger actually predicts."""
    bits = [user_note] if user_note else []
    if prior is None:
        bits.append("first balance on record")
    return " — ".join(b for b in bits if b)  # drift appended by caller once new_balance is known


def add_row(what: str, amount, note: str, date_str: str, dry: bool,
            explicit_balance=None):
    """Insert one ledger row and update Current balance, atomically.

    The prior balance is read and the new balance computed INSIDE the lock,
    from a fresh read of the file — never before acquiring it. Two
    concurrent calls used to both read the same stale prior and race each
    other to a wrong number even though the lock stopped the WRITE from
    tearing; see the design notes at the top of this file. This function is
    the only place that decides a new balance, and it always does so under
    `locked()`.

    Returns (row_text, new_balance, prior_balance_or_None).
    """
    what_safe = safe_cell(what)
    note_safe_prefix = safe_cell(note)

    if dry:
        # Read-only preview — safe without the lock since nothing is written.
        lines = NOTE_PATH.read_text(encoding="utf-8").split("\n") if NOTE_PATH.exists() else []
        prior = last_ledger_balance(lines)
        if explicit_balance is not None:
            new_balance = explicit_balance
            drift_note = _drift_text(prior, new_balance)
            note_full = " — ".join(b for b in [note_safe_prefix or None, drift_note] if b)
        else:
            if prior is None:
                fail(
                    "no starting balance in the ledger yet — run --set-balance first "
                    "so transactions have something to add to, e.g.:\n"
                    "  python3 AIOS/scripts/money.py --set-balance <amount> --note \"...\""
                )
            new_balance = prior + amount
            note_full = note_safe_prefix
        amount_cell = fmt_amount(amount) if amount is not None else "—"
        row = f"| {date_str} | {what_safe} | {amount_cell} | {fmt_balance(new_balance)} | {note_full} |"
        return row, new_balance, prior

    with locked(NOTE_PATH):
        if not NOTE_PATH.exists():
            fail(f"{NOTE_PATH} does not exist")
        text = NOTE_PATH.read_text(encoding="utf-8")
        lines = text.split("\n")

        prior = last_ledger_balance(lines)  # fresh, under the lock — the actual fix

        if explicit_balance is not None:
            new_balance = explicit_balance
            drift_note = _drift_text(prior, new_balance)
            note_full = " — ".join(b for b in [note_safe_prefix or None, drift_note] if b)
        else:
            if prior is None:
                fail(
                    "no starting balance in the ledger yet — run --set-balance first "
                    "so transactions have something to add to, e.g.:\n"
                    "  python3 AIOS/scripts/money.py --set-balance <amount> --note \"...\""
                )
            new_balance = prior + amount
            note_full = note_safe_prefix

        amount_cell = fmt_amount(amount) if amount is not None else "—"
        row = f"| {date_str} | {what_safe} | {amount_cell} | {fmt_balance(new_balance)} | {note_full} |"

        ledger_head = ensure_ledger_section(lines)
        header_idx, last_row_idx = find_ledger_table(lines)
        if header_idx is None:
            # ensure_ledger_section just created an empty table; recompute.
            header_idx = ledger_head + 4  # heading, blank, intro, blank -> LEDGER_COLS
            last_row_idx = header_idx + 1

        lines.insert(last_row_idx + 1, row)
        update_current_balance(lines, new_balance, date_str,
                                "transaction" if amount is not None else "balance check")

        write_atomic(NOTE_PATH, "\n".join(lines))
    return row, new_balance, prior


def _drift_text(prior, new_balance) -> str:
    if prior is None:
        return "first balance on record"
    drift = new_balance - prior
    if abs(drift) < 0.01:
        return "matches what the ledger predicted"
    return f"ledger predicted {fmt_balance(prior)} — drift {fmt_amount(drift)} unaccounted"


# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", nargs="?", help="what happened, e.g. 'New headphones'")
    ap.add_argument("amount", nargs="?", type=float,
                     help="+income/gift or -spend, e.g. -89.99")
    ap.add_argument("--set-balance", type=float, metavar="EUR",
                     help="reconcile: a real balance you just checked")
    ap.add_argument("--note", default="", help="free text for the Notes column")
    ap.add_argument("--date", help="YYYY-MM-DD, defaults to today")
    ap.add_argument("--list", action="store_true", help="print recent ledger rows")
    ap.add_argument("--last", type=int, default=10, help="how many, with --list")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.date:
        try:
            date_str = dt.date.fromisoformat(args.date).isoformat()
        except ValueError:
            fail(f"--date must be YYYY-MM-DD, got {args.date!r}")
    else:
        date_str = dt.date.today().isoformat()

    if args.list:
        if not NOTE_PATH.exists():
            fail(f"{NOTE_PATH} does not exist")
        lines = NOTE_PATH.read_text(encoding="utf-8").split("\n")
        header_idx, last_row_idx = find_ledger_table(lines)
        if header_idx is None or last_row_idx <= header_idx + 1:
            print("money: ledger is empty — nothing logged yet")
            return 0
        rows = lines[header_idx + 2: last_row_idx + 1][-args.last:]
        for r in rows:
            print(f"  {r}")
        return 0

    if args.set_balance is not None:
        if args.set_balance < 0:
            print("money: NOTE — negative balance, logging as overdrawn/negative on purpose "
                  "(not an error, just flagging it's unusual)", file=sys.stderr)
        row, new_balance, prior = add_row(
            "**Balance check**", None, args.note, date_str, args.dry_run,
            explicit_balance=args.set_balance,
        )
        label = "[dry-run] would log" if args.dry_run else "logged"
        print(f"money: {label} balance check — {row}")

        if not args.dry_run:
            what_changed = f"Balance check: {fmt_balance(new_balance)}" + (
                f" (drift {fmt_amount(new_balance - prior)})"
                if prior is not None and abs(new_balance - prior) >= 0.01 else ""
            )
            rel = P.relative(NOTE_PATH)
            subprocess.run(
                [sys.executable or "python3", str(P.SCRIPTS / "logchange.py"),
                 what_changed, rel],
                check=False,
            )
        return 0

    if not args.what or args.amount is None:
        ap.print_help()
        return 2

    row, new_balance, prior = add_row(args.what, args.amount, args.note, date_str, args.dry_run)
    label = "[dry-run] would log" if args.dry_run else "logged"
    print(f"money: {label} — {row}")

    if not args.dry_run:
        what_changed = f"Money: {args.what} ({fmt_amount(args.amount)}, balance now {fmt_balance(new_balance)})"
        rel = P.relative(NOTE_PATH)
        subprocess.run(
            [sys.executable or "python3", str(P.SCRIPTS / "logchange.py"),
             what_changed, rel],
            check=False,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
