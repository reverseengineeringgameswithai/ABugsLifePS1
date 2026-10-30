---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - Type-0x3f pickups are coordinate-moddable.md
aliases:
  - "Finding - Type-0x3f pickups are coordinate-moddable"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - Type-0x3f pickups are coordinate-moddable.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_Type-0x3f_pickups_are_coordinate-moddable.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Finding - Type-0x3f pickups are coordinate-moddable
type: finding
confidence: CONFIRMED
gstep: n/a (pickup track)
tags: [finding, dat, pickup, type3f]
---

# Finding — Type-0x3f pickups are coordinate-moddable

> Every LEVEL.DAT pickup (grain, FLIK letter, berry, seed token) can be moved in-game by a fixed-size edit to its type-0x3f entry. Confirmed in-game across all kinds.

**Confidence:** CONFIRMED (in-game)

## Summary
- Entry layout `+0=X +4=Y +8=Z` (s32 LE), `+0xc=kind`; **runtime coord = file coord `<< 5`**; more-negative Y = up.
- All kinds verified moveable with kind preserved: grain `0x14`, FLIK F/L/I/K `0x10–0x13`, special berries `0x21–0x24` (entries 54–57), seed tokens `0x29/0x2a/0x2b`.
- **Height-band rule:** auto-collect depends on absolute final runtime Y (weak-Y contact cylinder, [[FUNC_800586B0]] weights Y at ⅓), not on the delta size. Keep final runtime Y ≳ −21000.

## Evidence
- Many in-game builds (the `ABL_*_TEST` series): grain/FLIK/seed/berry moves all collected correctly; entry 65 failed at rt Y ≈ −30784 but passed at ≈ −18496 (established the band).
- ⚠️ Never change kind on entries 54–57 — that deletes a real berry (sacrifice test removed Gold/Super/Mega-Homing berries).

## Related functions
[[FUNC_8001CDC0]] (parse/relocate) · [[FUNC_80053814]] (construct) · [[FUNC_80059E44]] · [[FUNC_800586B0]] (contact)

## Related memory structures
[[MEM - Type-0x3f placement record]] · [[MEM - Contact array 800B0D18]]

## Related experiments
[[Experiment - DAT relocation-aware append]]

## Related fixtures / save states
n/a (disc builds; see [[Tools Catalog]])

## DuckStation APIs used
n/a (offline DAT patch + rebuild)

## Next steps
For *new* objects (not moves), use the relocation-aware append — see [[Finding - Relocation-aware DAT append]].

## Source
`ABL_RE_NOTES.md`, `docs/COORDINATE_MODDING.md`, `docs/LEVEL01_TYPE3F_MAP.md`, `docs/EXPERIMENT_LOG.md`
