---
title: canon
tags:
  - reference
  - generated
---

# canon

The register of facts that live in more than one note — the truth, which note
owns it, and the wording that's now wrong and shouldn't appear anywhere else.
Checked by `python3 AIOS/scripts/canon-check.py`.

**Empty at the start, on purpose.** Add a row the moment you correct a fact
that's repeated in more than one place — that's the whole maintenance burden,
and it's the point: correcting a fact and registering it are one action, not
two.

| # | Fact | Truth | Owner note | Stale wording | Allowed in | Since |
|---|---|---|---|---|---|---|
| | | | | | | |

Column notes:

- **Stale wording** — plain text, semicolon-separated, case-insensitive
  substrings. Not regex; a real sentence has commas, so commas can't be the
  separator.
- **Allowed in** — notes where the old wording is legitimately fine to still
  appear (e.g. a note explaining the correction itself). The owner note is
  always allowed automatically.
- Leave **Stale wording** as `—` for a fact worth recording but with nothing
  sensible to grep for — it'll be skipped by the check, not flagged as broken.

## Related

- [[Home]]
- [[vault-map]]
