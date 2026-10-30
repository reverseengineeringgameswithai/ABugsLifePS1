---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - fcn.80010000 payload format.md
aliases:
  - "Finding - fcn.80010000 payload format"
migration_action: split
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - fcn.80010000 payload format.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_fcn.80010000_payload_format.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Finding - fcn.80010000 payload format
type: finding
confidence: CONFIRMED
gstep: G11
tags: [finding, rendering, geometry, format]
---

# Finding — `fcn.80010000` mesh payload format decoded

> The per-object mesh format that the engine's main emitter draws. Decoding it unlocked every later vertex-edit experiment.

**Confidence:** CONFIRMED · **Established:** G11

## Summary
Payload = `{ u32 vertexCount; Vertex verts[N] (stride 0xc: s16 x; s16 y; s16 z; s16 pad=0; u32 attr); command stream }`. Command `ctrl` u16: `type = ctrl & 0x1f` dispatched via jump table `0x8001036C + type*8`; type-0 = triangle (cites 3 vertices by byte offset; RTPS/RTPT project, NCLIP backface-cull). Full layout in [[MEM - fcn.80010000 mesh payload]].

## Evidence
Static disasm of [[FUNC_80010000]] (triangle case `0x8001046c`) + byte trace of entry29 (count 34, v0=(0,-744,-61)) and entry0 (count 195). Lesson (G13): watch the aligned `lwc2` vertex base, not the inner s16.

## Related functions
[[FUNC_80010000]] · [[FUNC_8001EA6C]] · [[FUNC_800206E8]] · [[FUNC_80019934]]

## Related memory structures
[[MEM - fcn.80010000 mesh payload]]

## Related experiments
[[Experiment - G14 payload vertex grass]] · [[Experiment - G13 payload v0]]

## Related fixtures / save states
[[Fixture - g30 openfloor]]

## DuckStation APIs used
[[API - execTrace]] · [[API - accessLog]]

## Next steps
`attr` (vertex +0x8) role (UV/normal/color) and the count≤0 head path remain UNKNOWN.

## Source
`src_re_geometry/geometry_g11_payload_format.md`
