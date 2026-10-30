---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - Collision is planes not scalar.md
aliases:
  - "Finding - Collision is planes not scalar"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - Collision is planes not scalar.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_Collision_is_planes_not_scalar.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Finding - Collision is planes not scalar
type: finding
confidence: CONFIRMED
gstep: G29
tags: [finding, collision, physics]
---

# Finding — The collision floor is PLANES, not a scalar height

> Flik's footing is resolved against oriented plane records (normal + reference point), not a single floor-height value — which is why a simple "set Y" doesn't model it.

**Confidence:** CONFIRMED · **Established:** G29

## Summary
Each sector's `[+0x10]` points to 32-byte plane records (`~0x800D0xxx`): normal `+0/+2/+4`, reference point `+6/+8/+0xa`, face edges `+0xc..+0x16`. The resolver [[FUNC_800345CC]] computes a **swept plane-distance clamp** with a stop-with-skin offset (`−0xc0`), and a point-in-face test (`0x80032610`) gates it. The resolved Y is committed by [[FUNC_8003633C]] at `0x80036cec`.

## Evidence
Disasm of the resolver (`0x800347c4..0x80034b30`) + read-watches on the candidate records during a live move. Editing a sector *origin* shifts the whole plane set ~1:1 ([[Finding - Collision RAM edit moves footing 1to1]]).

## Related functions
[[FUNC_800345CC]] · [[FUNC_8003633C]] · [[FUNC_80030F60]]

## Related memory structures
[[MEM - Collision plane record]] · [[MEM - Collision sector table 800A7E48]]

## Related experiments
[[Experiment - G29 collision lever validation]]

## Related fixtures / save states
[[Fixture - g30 openground]]

## DuckStation APIs used
[[API - addWatch]] · [[API - accessLog]] · [[API - execTrace]]

## Next steps
A per-plane `refpt.y` lever needs a corrected winning-record capture (the `sp+0x88` read was buggy).

## Source
`src_re_geometry/geometry_g29_collision_source_plan.md`
