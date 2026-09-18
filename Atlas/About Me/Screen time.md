---
title: Screen time
tags:
  - about-me
---

# Screen time

Screen hours and sleep, logged when you state a number — not a nag, just the
data, so a pattern is visible if one ever matters. Filled by
`python3 AIOS/scripts/screentime.py --hours N [--sleep N]`. `--avg` for the
rolling average, `--check` for a silent-unless-triggered warning system (near-
zero night, sustained low average, a downward trend) meant to run from a
daily-brief-style routine.

## Log

%% Append-only, via `AIOS/scripts/screentime.py`. One row per day you state a
number for. %%

| Date | Screen hrs | Sleep hrs | Note |
|---|---|---|---|

## Related

- [[About Me]]
