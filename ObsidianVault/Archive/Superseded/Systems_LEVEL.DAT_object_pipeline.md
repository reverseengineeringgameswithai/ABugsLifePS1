---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/LEVEL.DAT object pipeline.md
aliases:
  - "LEVEL.DAT object pipeline"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/LEVEL.DAT object pipeline.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/LEVEL.DAT_object_pipeline.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: LEVEL.DAT object pipeline
type: system
tags: [system, dat, pickup, pipeline]
---

# LEVEL.DAT object pipeline (type-0x3f)

> The full path from a placement record on disc to a collectible entity with a HUD counter. Detail in `docs/LEVEL_OBJECT_PIPELINE.md`.

## Flow
```
LEVEL.DAT type-0x3f entry
  → [[FUNC_8001CDC0]]  (parse + relocate baked offsets; rebuild type table 0x80096da0)
  → type-0x3f ptr 0x80096e9c
  → [[FUNC_80053814]]  (per-entry source-kind pass: construct + contact-action dispatch)
  → [[FUNC_80059E44]]  (ContactRecord alloc into 0x800b0d18 from metadata tables A/B)
  → [[FUNC_800586B0]]  (proximity walker; weak-Y contact math; action dispatch)
  → per-kind handlers (grain [[FUNC_80054EAC]], berries, seed tokens, FLIK, telescope)
  → [[FUNC_800526F4]]  (HUD: grain/seed/FLIK meters)
```

## Record + coordinate rules
[[MEM - Type-0x3f placement record]]: `+0=X +4=Y +8=Z` (s32), `+0xc=kind`; **runtime = file `<< 5`**; more-negative Y = up. Entry ranges (LEVEL01): grain 0–49, FLIK 50–53, berries 54–57, seed tokens 58–66, **telescopes 67–69** (hint device; was "checkpoint" — corrected, [[Experiment - Pickup kind-swap]]). Kind→item map in [[Symbols Index]] / `docs/LEVEL01_TYPE3F_MAP.md`.

## Editing
Move existing: `tools/patch_level_entry.py`. Add new: `tools/dat_reloc.py` (relocation-aware — naive append black-screens, see [[Finding - Relocation-aware DAT append]]). ⚠️ never change kind on entries 54–57 (real berries).

## Tier-3 compatibility
[[Experiment - Tier3 native grain relocation]] confirmed that a native `type-0x3f` grain moved onto the Tier-3 custom
floor is constructed and collected through the native pickup/HUD path on the cold-boot Tier-3 render disc. Baseline
same movie ended with grain count `0`; relocated native grain ended with grain count `1`. [[Experiment - Tier3 native seed token relocation]] then confirmed the same path for a native orange seed token: baseline packed counter
`0x800a6598 = 0x11`, relocated-token counter `0x22`, entry consumed. [[Experiment - Tier3 native FLIK letter relocation]] confirmed entries 50-53 are real native FLIK-letter pickups: relocating all four onto the Tier-3
platform set FLIK bitmask `0x800a65a2 = 0x0f`, pulsed the FLIK HUD state, and consumed all four records. This
supports the GAP-T3-1/T3-3 decision to use native `type-0x3f` objects as the primary differentiated-object/counter
and collectible-set path for Tier 3.

## Related
- Findings: [[Finding - Type-0x3f pickups are coordinate-moddable]] · [[Finding - Relocation-aware DAT append]]
- Structures: [[MEM - Type-0x3f placement record]] · [[MEM - Contact array 800B0D18]]
- Asset: [[Asset - LEVEL.DAT]] · Tools: [[Tools Catalog]]
