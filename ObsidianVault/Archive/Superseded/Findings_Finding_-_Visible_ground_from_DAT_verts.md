---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - Visible ground from DAT verts.md
aliases:
  - "Finding - Visible ground from DAT verts"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - Visible ground from DAT verts.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_Visible_ground_from_DAT_verts.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Finding - Visible ground from DAT verts
type: finding
confidence: CONFIRMED
gstep: G30
tags: [finding, rendering, geometry, dat]
---

# Finding — Bulk visible foreground floor = `fcn.80010000` DAT objects

> The ground directly under Flik (the bulk foreground floor) is drawn by [[FUNC_80010000]] from LEVEL.DAT-backed objects, via the `0x80019xxx` sub-emitter.

**Confidence:** CONFIRMED · **Established:** G30 · **Findings-store id:** f13

## Summary
- [[FUNC_80019934]] (writer PCs `0x80019934/50/54/70`, rtpt `0x80019684/0x80019734`) is a sub-emitter under [[FUNC_80010000]] (ra `0x800108b8`).
- Source objects `a0 = 0x80178590 / 0x80177b7c` are in **LEVEL.DAT**; `s7` = scratchpad work context.
- Vertex = 12 bytes `[c0, c1, Z, pad, X, Y]`; **edit lever = int16 Y at vert+0xa** (flat height; span 68 vs X span 63480).
- This is the **same** `fcn.80010000` / Candidate-A system that G28 proved editable — see [[Finding - Candidate A is DAT-backed visual terrain]].

## Evidence
- s7/a0 trace identified the LEVEL.DAT source; lowering vert Y changed **38090 px** of the visible floor (diff-confirmed).
- Index→screen: obj1 verts `[0:24]` = the foreground under Flik. Gouraud 0x3C tiles → Y-edit reshades (low=yellow, high=purple); geometric drop is subtle (foreshorten + camera-follow-Y); big edit garbages (frustum); clean range ≈ ±0x20…0x60.

## Related functions
[[FUNC_80010000]] · [[FUNC_80019934]] · [[FUNC_8001EA6C]] · [[FUNC_800172DC]] (broad terrain surface, distinct)

## Related memory structures
[[MEM - fcn.80010000 mesh payload]]

## Related experiments
[[Experiment - G30 localized terrain edit]] · [[Experiment - G28 Candidate A floor Y]]

## Related fixtures / save states
[[Fixture - g30 openfloor]] (best view) · [[Fixture - g30 openground]]

## DuckStation APIs used
[[API - execTrace]] · [[API - accessLog]] · [[API - scatterWrite]] · [[API - gpu.readVramRect]] · [[API - visual diff]]

## Next steps
Pin each foreground emitter's `s7` build-context origin for a clean multi-emitter floor edit; combine with the matched collision lever ([[Finding - Visual is not collision]]).

## Source
`src_re_geometry/geometry_g30_terrain_render_source_plan.md` §20; findings-store f13
