---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - No static collision consumer.md
aliases:
  - "Finding - No static collision consumer"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - No static collision consumer.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_No_static_collision_consumer.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Finding - No static collision consumer
type: finding
confidence: CONFIRMED
gstep: G5 (vindicated G29)
tags: [finding, collision, method]
---

# Finding — No static global scan finds a collision consumer of parser geometry

> A negative result that turned out to be *true and important*: collision reaches its data through a non-global pointer chain, so a static global-reference scan can't see it.

**Confidence:** CONFIRMED (negative) · **Established:** G5 · **Vindicated:** G29

## Summary
A lui-tracking static scan of the parser-geometry globals found **no** collision/pathing consumer: ~40 functions read player position `0x800a6500/04/08` but none holds a parser-geometry handle. The only oriented test found ([[FUNC_80025084]]) reads actor/object data, not parser geometry. This looked like a dead end — but G29 showed why: collision reaches its data via `[sector+0x10]` (a pointer stored in the runtime-built sector table), invisible to a static global scan.

## Evidence
G5 static scan (negative); G29 live trace found the actual chain (sector table `0x800a7e48` → plane records → resolver), confirming the floor source is *not* reachable from a static global ([[Finding - Collision sector table]]).

## Related functions
[[FUNC_80025084]] · [[FUNC_8003633C]] · [[FUNC_8005B134]]

## Related memory structures
[[MEM - Collision sector table 800A7E48]] · [[MEM - Player state 800A6500]]

## Related experiments
[[Experiment - G29 collision lever validation]]

## Related fixtures / save states
[[Fixture - g30 openground]]

## DuckStation APIs used
Static (r2) for G5; [[API - addWatch]] / [[API - accessLog]] for the G29 vindication.

## Next steps
Method lesson → when static scans fail, switch to a live WRITE-watch on the *effect* (player Y) and walk back — see [[Playbook - Trace collision resolution]].

## Source
`src_re_geometry/geometry_notes.md` (G5), `geometry_g29_collision_source_plan.md`
