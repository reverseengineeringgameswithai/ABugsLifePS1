---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Functions/FUNC_80046330.md
aliases: []
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Functions/FUNC_80046330.md`
- Replacement/current location: `ObsidianVault/Canon/Functions/FUNC_80046330_universal_file_loader.md`
- Archive reason: Existing function note; migrate only evidence-backed claims and link C source where available.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: FUNC_80046330 — universal file loader
type: function
address: 0x80046330
confidence: CONFIRMED
tags: [function, loader, cd]
---
# FUNC_80046330 — universal file loader

> The single choke point through which every level file read passes. `(filename, dest) → bytes read`.

| Field | Value |
|-------|-------|
| Address | 0x80046330 |
| Source file | disasm (G19–G22); `geometry_runtime_buffers.c`, `geometry_collision_consumers.c` |
| Confidence | CONFIRMED loader ABI |

## Purpose
`fcn.80046330(a0 = bare filename string, a1 = destination base) → v0 = bytes read`. Prepends the CD/level directory; all 14 file-read sites in the engine funnel through it.

## Arguments / Returns
`a0` = filename, `a1` = destination RAM base. Returns byte count.

## Calls (callees)
- CD subsystem (libcd) primitives (not decompiled here).

## Called by (callers)
- 14 call sites across 11 functions. Key: [[FUNC_8003CF2C]] (LEVEL.DAT, hit #6 `a1=0x801607f8`) and [[FUNC_8003A318]] (LEVEL.RAW, **hit #4** `ra=0x8003a390`, dest `0x80115aac`, size `0xb6be4`).
- Filename builder `fcn.80046618` constructs `LEVEL0N\LEVEL[M].BIN`.

## Globals & structures touched
- Writes to whatever `a1` points at (DATbase, LEVEL.RAW buffer, overlay regions).

## Evidence & confidence notes
G21/G22 watched the callee entry to bracket the floor resource — hit #4 identified LEVEL.RAW (dest-size `0x801cc390 − 0x80115aac = 0xb68e4` matches the file exactly). See [[Finding - Floor resource is LEVEL.RAW]].

## Related
- Findings: [[Finding - Floor resource is LEVEL.RAW]] · [[Finding - LEVEL.RAW is compressed]]
- Functions: [[FUNC_8003A318]] · [[FUNC_8003CF2C]] · [[FUNC_8001A1DC]]
- Assets: [[Asset - LEVEL.RAW]] · [[Asset - LEVEL.BIN and overlays]]
- Source docs: `src_re_geometry/geometry_g21_file_read_caller_map.md`, `geometry_g22_high_heap_floor_source.md`
