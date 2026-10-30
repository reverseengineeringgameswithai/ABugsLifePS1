---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - Payload vertex edits are visible.md
aliases:
  - "Finding - Payload vertex edits are visible"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - Payload vertex edits are visible.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_Payload_vertex_edits_are_visible.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Finding - Payload vertex edits are visible
type: finding
confidence: CONFIRMED
gstep: G14
tags: [finding, rendering, geometry, method]
---

# Finding — Payload-vertex edits visibly deform geometry

> Editing a command-stream-referenced vertex Y in a DAT payload produces a visible deformation in-game — the first end-to-end proof that the vertex-edit method works.

**Confidence:** CONFIRMED · **Established:** G14

## Summary
G14 edited entry29's command-referenced silhouette vertex v14.y (`DAT 0x2f3a6`, −1024) and the rendered object (grass/decor) visibly deformed. Key method lesson from G13: pick a vertex the **command stream actually references**, and watch the aligned `lwc2` base — an unreferenced/inner-s16 edit reads but doesn't show.

## Evidence
G14 build `ABL_G14_ENTRY29_PAYLOAD_VERTEX_TEST` = VISIBLE change (vs G12/G13/G15 which were read-confirmed but visually silent). The object was decor, not floor — leading to the floor hunt (G15→G28).

## Related functions
[[FUNC_80010000]]

## Related memory structures
[[MEM - fcn.80010000 mesh payload]]

## Related experiments
[[Experiment - G14 payload vertex grass]] · [[Experiment - G13 payload v0]] · [[Experiment - G16 emitted payload vertex wall]]

## Related fixtures / save states
n/a (disc build)

## DuckStation APIs used
[[API - execTrace]] · [[API - accessLog]]

## Next steps
Generalized to floor in G28 ([[Finding - Candidate A is DAT-backed visual terrain]]).

## Source
`src_re_geometry/geometry_g11_payload_format.md` §5
