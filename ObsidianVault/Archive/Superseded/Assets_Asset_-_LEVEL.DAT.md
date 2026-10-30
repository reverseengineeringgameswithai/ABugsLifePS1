---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Assets/Asset - LEVEL.DAT.md
aliases:
  - "Asset - LEVEL.DAT"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Assets/Asset - LEVEL.DAT.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Asset_-_LEVEL.DAT.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Asset - LEVEL.DAT
type: asset
confidence: CONFIRMED
tags: [asset, dat, pickup, geometry]
---
# Asset — LEVEL.DAT

> Per-level object/placement + geometry-payload container. The most-modded file in the project.

## Summary
`files/LEVEL01/LEVEL.DAT` holds the level's object placements (type-0x3f pickups), trailing relocation tables, source records, and the mesh **payload band**. Parsed at runtime by [[FUNC_8001CDC0]], which relocates 1248 baked file-offset fields by adding the load base.

## Format / layout
- First top-level record = **type 0x3f** at file `0x4` (header `46 00 3f 00` = count LE u16 + type). Entries at file `0x8`, stride `0x10`. See [[MEM - Type-0x3f placement record]].
- Top-level records end at `0x1500`; trail base `0x1504`; PASS1 table `0x1512` (stride 0x14, 484); PASS3 `0x3afa` (stride 0x14, 140); source-record band `0x45f0..0x8bd8`; **payload band `0x8bd8..0x4f32c`** (the `fcn.80010000` meshes — see [[MEM - fcn.80010000 mesh payload]]); EOF `0x51418`.
- Coordinate rule: runtime = file `<< 5`.

## Where it lives
- **Disk:** image LBA **2906**; pristine size **332824** (`0x51418`); pristine sha1 `b376cb506f437a1cda721fd13766ddbca7c6a247`.
- **Runtime:** base `[0x80082498] = 0x801607F8`; image `[0x801607f8, 0x801b1c10)`; pass-1 output records `[0x801b1c10, 0x801b5890)`.

## How it's loaded / parsed
`fcn.8003cf2c` (resource dispatcher) reads the file via [[FUNC_80046330]] then calls [[FUNC_8001CDC0]] once (`a1=0x51418`). See [[LEVEL.DAT object pipeline]].

## Edit path
- Move pickups: `tools/patch_level_entry.py` / `tools/move_type3f_entry.py`.
- Append new: `tools/dat_reloc.py` + `tools/insert_type3f_entries.py` (relocation-aware) — see [[Experiment - DAT relocation-aware append]].
- Edit visual terrain mesh: patch the payload band (e.g. Candidate A) — see [[MEM - fcn.80010000 mesh payload]], [[Experiment - G28 Candidate A floor Y]].

## Related
- Findings: [[Finding - Type-0x3f pickups are coordinate-moddable]] · [[Finding - Relocation-aware DAT append]] · [[Finding - Candidate A is DAT-backed visual terrain]]
- Functions: [[FUNC_8001CDC0]] · [[FUNC_80010000]] · Structures: [[MEM - Type-0x3f placement record]] · [[MEM - fcn.80010000 mesh payload]] · [[MEM - DAT runtime memory map]]
- Tools: [[Tools Catalog]] · Docs: `docs/DAT_FORMAT_AND_RELOCATION.md`, `docs/LEVEL_OBJECT_PIPELINE.md`
