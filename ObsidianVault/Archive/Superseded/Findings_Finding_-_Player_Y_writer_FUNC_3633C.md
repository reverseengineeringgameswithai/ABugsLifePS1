---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - Player Y writer FUNC_3633C.md
aliases:
  - "Finding - Player Y writer FUNC_3633C"
migration_action: split
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - Player Y writer FUNC_3633C.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_Player_Y_writer_FUNC_3633C.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Finding - Player Y writer FUNC_3633C
type: finding
confidence: CONFIRMED
gstep: G29
tags: [finding, collision, physics]
---

# Finding — Player-Y writer is `fcn.8003633c` (not `fcn.8005b134`)

> The per-frame routine that resolves and commits Flik's floor-corrected Y is [[FUNC_8003633C]]. This **supersedes** the earlier static guess of `fcn.8005b134`.

**Confidence:** CONFIRMED · **Established:** G29

## Summary
- [[FUNC_8003633C]] is the per-frame movement + collision-response integrator. For the player (`a0/s7 = 0x800a6500`) it commits the collision-resolved Y to player Y `0x800a6504` at PC **`0x80036cec`** (the decisive store).
- Callers: `0x800495c8 / 0x8004c024 / 0x8004e628`. Probe-bias stores `±0xc80` at `0x80036380 / 0x80036d54`.
- The previously-claimed writer **`fcn.8005b134`** (see [[FUNC_8005B134]]) has **zero jal callers** (it's overlay/jump-table dispatched) and is NOT the per-frame Y writer. Their relationship is still UNKNOWN.

## Evidence
- WRITE-watch on player Y `0x800a6504` while moving Flik (live JSON-RPC debugger) pinned the writing PC to `0x80036cec` inside `fcn.8003633c`; a jal-caller scan found the three callers.
- The store reads from `[sp+0x1c]`, the collision-resolved Y from resolver `0x800345cc`.

## Related functions
[[FUNC_8003633C]] · [[FUNC_800345CC]] · [[FUNC_80030F60]] · [[FUNC_8005B134]] (superseded claim)

## Related memory structures
[[MEM - Player state 800A6500]] · [[MEM - Collision sector table 800A7E48]] · [[MEM - Collision plane record]]

## Related experiments
[[Experiment - G29 collision lever validation]]

## Related fixtures / save states
[[Fixture - g30 openground]]

## DuckStation APIs used
[[API - addWatch]] · [[API - accessLog]] · [[API - controller input]] · [[API - frame capture]]

## Next steps
Resolve the `fcn.8005b134` ↔ `fcn.8003633c` relationship; capture the winning collision record for a single-plane (refpt.y) lever.

## Source
`src_re_geometry/geometry_g29_collision_source_plan.md`
