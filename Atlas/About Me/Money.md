---
title: Money
tags:
  - about-me
---

# Money

Your real balance and spending, tracked so an AI can answer "how much do I
have" without you checking your bank app first. Filled and updated by
`python3 AIOS/scripts/money.py` — see that script's docstring, or the `money`
routine in `AIOS/skill-map.md`.

## Right now

| | |
|---|---|
| Current balance | *(run `money.py --set-balance <amount> --note "..."` once to fill this in)* |

## Ledger

%% Append-only, via `AIOS/scripts/money.py`. One row per logged transaction
or balance correction — never edit a past row, only add new ones. The
`Current balance` row above is derived from the last row here. %%

| Date | What | Amount | Balance | Notes |
|---|---|---|---|---|

## Related

- [[About Me]]
