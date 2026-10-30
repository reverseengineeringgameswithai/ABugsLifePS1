---
kind: function
id: LEGACY_FUNC_80025084_oriented_containment_range_test
aliases: [LEGACY_FUNC_80025084_oriented_containment_range_test, oriented_containment_-_range_test]
address: 0x80025084
name: oriented_containment_-_range_test
status: superseded
canonical_address: false
superseded_by: FUNC_80025084_enemy_spawn_visibility
confidence: confirmed
source_state: original_game
system: []
calls: []
reads: []
writes: []
uses_tables: []
related_constants: []
related_hooks: []
evidence: []
src_paths: []
patch_policy: unknown
---

# FUNC_80025084 - oriented containment - range test

## Purpose

An oriented bounding/containment test on actor/object data. A G5/G29 wall-or-ledge collision candidate — notably it reads **no parser geometry**. **Slide resolution (`0x80025170`+):** a *second* dot product against a **tangent** vector (`0x80090fb0/fb2/fb4`) gives `tangential = dot(delta, tangent) >> 17` = position *along* the wall — so the wall is an oriented **segment** (normal + tangent basis). Collision requires within `radius` perpendicular **and** within the segment span tangentially; resolution **corrects the normal component (stop) and preserves the tangential (slide along the wall)**. The caller `fcn.8004d224` iterates this over walls (the slide/re-test loop). **Fixture:** `SCUS-94288_fence_wall.sav` — Flik at the openfloor fence; holding ↑ re-fires this function. Saved 2026-06-18.

## Known behavior

This page is a copy-first Canon seed generated from `ObsidianVault/Functions/FUNC_80025084.md`. Treat claims as Canon only to the status/confidence level above. Do not promote stale or speculative material without evidence from `_Revamp/CONFLICTS.md` and linked experiments.

## Address / identity

- Address: `0x80025084`
- Name: `oriented_containment_-_range_test`
- Original note: `ObsidianVault/Functions/FUNC_80025084.md`
- Source path: `none matched`

## C source excerpt

Source: `none matched`

```c
// No matching C source found during revamp audit.
```

## Evidence

- Original note: `ObsidianVault/Functions/FUNC_80025084.md`
- Source coverage row: `_Revamp/SRC_COVERAGE.md`

## Related

See `Canon/Indexes/Address Index.md` and `_Revamp/MIGRATION_MAP.md`.

## Legacy Migration Reference

- Legacy source archived from `ObsidianVault/Functions/FUNC_80025084.md`.
- Archive copy: `ObsidianVault/Archive/Superseded/Functions_FUNC_80025084.md`.
- Added during the 2026-07-08 migration completion pass; the archive copy is provenance, not current Canon.
