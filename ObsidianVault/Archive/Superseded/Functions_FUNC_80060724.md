---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Functions/FUNC_80060724.md
aliases: []
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Functions/FUNC_80060724.md`
- Replacement/current location: `ObsidianVault/Canon/Functions/FUNC_80060724_libgte_transform_leaf_bank.md`
- Archive reason: Existing function note; migrate only evidence-backed claims and link C source where available.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: FUNC_80060724 — libgte transform leaf bank
type: function
address: 0x80060724
confidence: CONFIRMED
tags: [function, rendering, gte, g30]
---
# FUNC_80060724 — shared libgte RotTransPers transform leaf

> A shared libgte transform leaf (reads source verts a0–a3, writes screen XY). The render layer earlier G-work missed because it only searched the inline `0x8001xxxx` rtps sites.

| Field | Value |
|-------|-------|
| Address | 0x80060724 (leaf bank `0x80060650–0x80060814`; sibling `0x800607a4`) |
| Source file | disasm (G30) |
| Confidence | CONFIRMED |

## Purpose
Shared libgte RotTransPers-style leaf: transforms source vertices (a0–a3) and writes the resulting SXY to `[sp+0x10..]`. This `0x80022–0x80025` caller layer was invisible to prior G-work (which only searched `0x8001xxxx` inline rtps) — finding f7.

## Arguments / Returns
`a0–a3` = source vertices; writes SXY to the stack.

## Calls (callees)
- GTE ops (leaf).

## Called by (callers)
- `0x800247b8` (decor/fence `0x801a6xxx`), `0x8002574c / 0x80025bd8` (props from LEVEL.DAT `0x80160xxx`), `0x80022c4c` (Flik shadow).

## Globals & structures touched
- source vertex banks `0x801a6xxx` (fence), `0x80160xxx` (props).

## Evidence & confidence notes
G30 R1 identified this leaf bank as the missed render layer (findings store id f7). It is distinct from the terrain surface renderer [[FUNC_800172DC]] and the mesh emitter [[FUNC_80010000]].

## Related
- Findings: [[Finding - Visible terrain renderer]]
- Functions: [[FUNC_800172DC]] · [[FUNC_80010000]] · [[FUNC_800224EC]] · [[FUNC_8001DFE4]]
- Source docs: `src_re_geometry/geometry_g30_terrain_render_source_plan.md` §12-14
