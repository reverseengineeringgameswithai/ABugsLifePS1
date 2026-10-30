---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Assets/Assets.md
aliases:
  - "Assets"
migration_action: convert_to_canon
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Assets/Assets.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Assets.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Assets
type: hub
tags: [hub, assets]
---

# Assets — Map of Content

> The game's data files and how to edit/rebuild them.

## Files
- [[Asset - LEVEL.DAT]] — object placements (type-0x3f) + geometry payloads; parsed/relocated by [[FUNC_8001CDC0]].
- [[Asset - LEVEL.RAW]] — compressed terrain + collision (chunks 35 / 32); decompressed by [[FUNC_8001A1DC]].
- [[Asset - LEVEL.BIN and overlays]] — per-level code overlays + per-object `OVL/*.BIN` models.
- [[Asset - Disc image and rebuild]] — pristine image + mkpsxiso rebuild workflow.

## Editing
- Pickups / placements: [[Tools Catalog]] (`patch_level_entry.py`, `dat_reloc.py`). See [[Finding - Type-0x3f pickups are coordinate-moddable]] · [[Finding - Relocation-aware DAT append]].
- Visual geometry: DAT payload vertex edits ([[Finding - Candidate A is DAT-backed visual terrain]]) — disc-buildable today.
- Terrain/collision in LEVEL.RAW: RAM/save-state edits work now; permanent disc edits blocked by the [[Finding - LEVEL.RAW is compressed|LZ codec]].

## Structures
[[MEM - Type-0x3f placement record]] · [[MEM - fcn.80010000 mesh payload]] · [[MEM - LEVEL.RAW chunk model]] · [[MEM - DAT runtime memory map]]

## Catalogs (source)
`DAT/type3f_catalog.md` (3661 rows), `DAT/grain_coordinate_catalog.md`, `DAT/phase6_cross_level.md`, `docs/LEVEL01_TYPE3F_MAP.md`.
