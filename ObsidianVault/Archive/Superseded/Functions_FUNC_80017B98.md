---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Functions/FUNC_80017B98.md
aliases: []
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Functions/FUNC_80017B98.md`
- Replacement/current location: `ObsidianVault/Canon/Functions/FUNC_80017B98_GTE_rotation-matrix_setup.md`
- Archive reason: Existing function note; migrate only evidence-backed claims and link C source where available.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: FUNC_80017B98 — GTE rotation-matrix setup
type: function
address: 0x80017B98
confidence: CONFIRMED
tags: [function, gte, geometry]
---
# FUNC_80017B98 — GTE rotation-matrix setup

> Builds a 3×3 rotation matrix from an angle triple. Shared by the DAT parser (fills output-record matrices) and the render driver (view matrix). Relocates nothing.

| Field | Value |
|-------|-------|
| Address | 0x80017B98 |
| Source file | referenced in `dat_parser_8001cdc0.c`, `dat_geometry_records.c`, `geometry_render_consumers.c` |
| Confidence | CONFIRMED role; internals not decompiled |

## Purpose
Builds a 3×3 rotation matrix from `angle[3]` (using the sin/cos table `0x80074970`), writing it to the destination. Used to fill the per-entry rotation matrices in [[MEM - Parser output record]] during parsing, and to set up the camera/view matrix during rendering.

## Arguments / Returns
`a0` = angle inputs, `a1`/out = destination matrix. Returns the matrix.

## Calls (callees)
- sin/cos table lookups.

## Called by (callers)
- [[FUNC_8001CDC0]] (parser, per pass-1 entry) and [[FUNC_800224EC]] (render driver, view matrix).

## Globals & structures touched
- sin/cos table `0x80074970`; writes [[MEM - Parser output record]] matrices.

## Evidence & confidence notes
CONFIRMED role from both call sites; it relocates no pointers (purely computes a matrix). Internals not fully decompiled.

## Related
- Functions: [[FUNC_8001CDC0]] · [[FUNC_800224EC]] · [[FUNC_800140A0]]
- Memory: [[MEM - Parser output record]]
- Source docs: `src_re/dat_parser_8001cdc0.c`, `geometry_render_consumers.c`
