---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Functions/FUNC_80019934.md
aliases: []
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Functions/FUNC_80019934.md`
- Replacement/current location: `ObsidianVault/Canon/Functions/FUNC_80019934_bulk-ground_sub-emitter.md`
- Archive reason: Existing function note; migrate only evidence-backed claims and link C source where available.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: FUNC_80019934 — bulk-ground sub-emitter
type: function
address: 0x80019934
confidence: CONFIRMED
tags: [function, rendering, terrain, dat, g30]
---
# FUNC_80019934 — bulk visible-ground sub-emitter (0x80019xxx)

> The `0x80019xxx` sub-emitter that draws the **bulk visible foreground floor** as DAT-backed objects, calling [[FUNC_80010000]] to project them. `0x80019934` is one of its vertex-writer PCs.

| Field | Value |
|-------|-------|
| Address | 0x80019934 (writer PCs `0x80019934/50/54/70`; rtpt `0x80019684/0x80019734`) |
| Source file | disasm only (G30 live trace) |
| Confidence | CONFIRMED (Y-edit changed ~38090 px of visible floor) |

## Purpose
Sub-emitter under the render chain that draws DAT-backed objects making up the bulk under-Flik / foreground floor. Reads source object data (a0 = `0x80178590` / `0x80177b7c`, in LEVEL.DAT) and emits via [[FUNC_80010000]] (ra `0x800108b8`). Vertex format here = 12-byte `[c0,c1,Z,0pad,X,Y]`; **edit lever = int16 Y at vert+0xa** (flat height, span 68 vs X 63480).

## Arguments / Returns
`a0` = DAT-backed object source (`0x80178590`/`0x80177b7c`); `s7` = scratchpad work/build context. Emits packets via [[FUNC_80010000]].

## Calls (callees)
- [[FUNC_80010000]] (per-object mesh draw).

## Called by (callers)
- The render driver chain ([[FUNC_800224EC]] → scene path). Part of the same `fcn.80010000` / Candidate-A system that G28 proved editable.

## Globals & structures touched
- LEVEL.DAT object data at `0x80178590` / `0x80177b7c`. See [[MEM - fcn.80010000 mesh payload]].

## Evidence & confidence notes
G30 §20: lowering the int16 Y `@vert+0xa` changed the visible floor (~38090 px); index→screen `obj1[0:24]` = foreground under Flik. Gouraud 0x3C tiles → Y-edit reshades (low=yellow, high=purple); big edit garbages (frustum); clean range ≈ ±0x20…0x60. Findings store id f13.

## Related
- Findings: [[Finding - Visible ground from DAT verts]] · [[Finding - Candidate A is DAT-backed visual terrain]] · [[Finding - Visual is not collision]]
- Functions: [[FUNC_80010000]] · [[FUNC_800172DC]] (the other visible-terrain path)
- Fixture: [[Fixture - g30 openfloor]] · Source docs: `src_re_geometry/geometry_g30_terrain_render_source_plan.md`
