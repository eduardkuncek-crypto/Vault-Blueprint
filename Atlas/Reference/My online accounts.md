---
title: My online accounts
tags:
  - reference
---

# My online accounts

Every account you've signed up for, so nothing sits unverified forever and
nothing gets paid for twice. Filled by
`python3 AIOS/scripts/accounts-audit.py --add "<name>"` (just signed up,
needs verifying) or `--add-active "<name>"` (already verified, in use).
`--check` ages every row in **Needs action** and flags anything unverified
14+ days.

## Needs action

%% Just signed up, not yet verified/confirmed. `--check` flags anything
sitting here 14+ days. %%

| Account | State | Since |
|---|---|---|

## Signed up, in use

%% Verified and actually being used. %%

| Account | Since |
|---|---|

## Related

- [[Reference]]
