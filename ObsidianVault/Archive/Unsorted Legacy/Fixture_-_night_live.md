---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Fixtures/Fixture - night live.md
aliases:
  - "Fixture - night live"
migration_action: needs_review
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Fixtures/Fixture - night live.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Fixture - night live
type: fixture
confidence: CONFIRMED
save_state: "SCUS-94288_night_live.sav"
tags: [fixture, savestate, rendering, sky, night]
---

# Fixture — night live (persistent playable night)

`~/.local/share/duckstation/savestates/SCUS-94288_night_live.sav`

Loads straight into the **persistent nighttime mod**: a big bright full moon (craters + glow) and dim stars over a smooth dark sky, drawn by a per-frame back-buffer hook — **flicker-free and playable** (Flik walks, scene renders normally). The hook code, night display-list, sky-cache patch, and the `jr ra` neutralization of the haze routine all live in the saved RAM, so loading the state restores the whole effect.

## Reproduce / rebuild from scratch
`tools/abl_night_hook.py`: load [[Fixture - starry night workbench]], then `Starry().reload_clean(); install(s)`.

## Verified
Loads → moon present, navy sky (no haze), scene intact, **0 corrupt frames** across stills + an 18-frame walk. Screenshots `starry_night_result/06_persistent_moon_static.png`, `07_persistent_moon_walking.png`.

## Related
[[Finding - Persistent night render hook]] · [[Experiment - Persistent nighttime render hook]] · [[FUNC_8003E928]] · [[MEM - OT output buffer pointer 8008240C]] · [[Fixture - starry night workbench]] · [[Save States Index]]
