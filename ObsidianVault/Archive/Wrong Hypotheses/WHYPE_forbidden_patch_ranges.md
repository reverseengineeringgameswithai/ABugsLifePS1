---
kind: wrong_hypothesis
id: WHYPE_forbidden_patch_ranges
status: resolved_wrong
confidence: confirmed
resolved_by:
  - ObsidianVault/_Revamp/CONFLICTS.md
  - ObsidianVault/Canon/Hooks/HOOK_forbidden_patch_ranges.md
  - src_re/known_crash_cave_hazards.c
---

# WHYPE_forbidden_patch_ranges

## Wrong claims

- `0x80082030` can be reused as custom berry descriptor space.
- `0x80081058..0x800810A4` is safe helper/code-cave space.

## Resolution

Wrong.

- `0x80082030..0x8008203C` is native berry/seed descriptor memory. Overwriting it caused seed/mega color regressions.
- `0x80081058..0x800810A4` was zeroed during a live ALLMODS boot. Do not place helper code there.

## Canon destination

- `Canon/Hooks/HOOK_forbidden_patch_ranges.md`
