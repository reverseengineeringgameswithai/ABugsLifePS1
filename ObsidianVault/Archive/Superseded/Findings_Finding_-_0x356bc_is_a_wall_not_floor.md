---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - 0x356bc is a wall not floor.md
aliases:
  - "Finding - 0x356bc is a wall not floor"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - 0x356bc is a wall not floor.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_0x356bc_is_a_wall_not_floor.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Finding - 0x356bc is a wall not floor
type: finding
confidence: CONFIRMED
gstep: G16
tags: [finding, rendering, geometry]
---

# Finding — Payload `0x356bc` is a wall, not the floor

> Emit-in-view is **necessary but not sufficient** for "floor": an emitted, on-screen payload turned out to be a vertical cliff face.

**Confidence:** CONFIRMED · **Established:** G16

## Summary
G16 picked an *emitted* payload (`0x356bc`, runtime `0x80195eb4`, flatness 0.48, Y-band 1354) by logging the packet-store gate `0x800108b4`, then edited v10.y (`DAT 0x3573a`, −1024). The result was a **visible wall/vertical-face deformation**, not a floor — reclassifying e128 as a wall and forcing the flatness-based floor search (G17→G27).

## Evidence
Build `ABL_G16_EMITTED_PAYLOAD_VERTEX_TEST` = visible cliff deform. Note: at `0x800108b4`, `a0` = vertex base, so payload = `a0−4`; the SXY words there are reused packet words (read the `s3` packet or BP `0x80010718` for true SXY).

## Related functions
[[FUNC_80010000]]

## Related memory structures
[[MEM - fcn.80010000 mesh payload]]

## Related experiments
[[Experiment - G16 emitted payload vertex wall]]

## Related fixtures / save states
n/a (disc build)

## DuckStation APIs used
[[API - execTrace]]

## Next steps
Floor needs flat + tight Y-band + lower-center screen → led to Candidate A ([[Finding - Candidate A is DAT-backed visual terrain]]).

## Source
`src_re_geometry/geometry_g16_screen_space_vertex_selection.md`
