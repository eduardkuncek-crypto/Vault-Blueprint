---
title: setup — run history
tags:
  - generated
---

# setup — run history

> [!info] Generated — do not edit by hand
> Appended by `scriptlog.py` every time `setup.py` runs. Newest run at the bottom.

## Runs

### 2026-08-14 23:24:43 — OK (0.21s)

args: `['--check']`

```text
Vault setup — this machine (dry run)
  vault:  /sessions/rcw-015sa5yknpnwwh626duyzzay/mnt/Vault Blueprint
  system: Linux 6.8.0-124-generic

  [ok]   Python 3.10.12
  [ok]   would create AIOS/history/chat-history/cowork, AIOS/history/chat-history/cowork-raw, AIOS/history/scripts, AIOS/generated, AIOS/archive, AIOS/code
  [ok]   scheduler available: cron (cron)
  [YOU]  backup-cowork is NOT correctly scheduled yet for this vault (a differently-pathed job with the same name doesn't count)
           python3 "/sessions/rcw-015sa5yknpnwwh626duyzzay/mnt/Vault Blueprint/AIOS/scripts/backup-cowork.py" --install-schedule --every-min 60
  [YOU]  changelog-check is NOT correctly scheduled yet for this vault (a differently-pathed job with the same name doesn't count)
           python3 "/sessions/rcw-015sa5yknpnwwh626duyzzay/mnt/Vault Blueprint/AIOS/scripts/changelog-check.py" --install-schedule --every-min 30
  [YOU]  vault-snapshot is NOT correctly scheduled yet for this vault (a differently-pathed job with the same name doesn't count)
           python3 "/sessions/rcw-015sa5yknpnwwh626duyzzay/mnt/Vault Blueprint/AIOS/scripts/vault-snapshot.py" --install-schedule --every-min 10
  [ok]   vault-check.py: clean
  [ok]   canon-check.py: clean

  Things a script must not do for you:

   * Obsidian: https://obsidian.md — or your distro's package,
     e.g. flatpak install flathub md.obsidian.Obsidian
     Then: Open folder as vault -> this folder.
   * Claude (Cowork or Claude Code), if it isn't already what you're
     using to read this: https://claude.ai/download
   * A sync folder (Dropbox, Syncthing, iCloud Drive...) if you want
     this vault to reach more than one machine. Optional.
   * git, only if you want the optional version-history snapshot:
       sudo apt install git

  Nothing was changed.

  Now run: python3 AIOS/scripts/setup-check.py
  for the full picture of what's actually working.
```
