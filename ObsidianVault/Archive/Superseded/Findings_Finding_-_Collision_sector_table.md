---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - Collision sector table.md
aliases:
  - "Finding - Collision sector table"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - Collision sector table.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_Collision_sector_table.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Finding - Collision sector table
type: finding
confidence: CONFIRMED
gstep: G29
tags: [finding, collision]
---

# Finding — Collision source is the sector table + plane records

> Flik's footing comes from a broadphase **sector table** at `0x800a7e48` that indexes 32-byte **plane records** — built from LEVEL.RAW chunk 32, entirely separate from the visual mesh.

**Confidence:** CONFIRMED · **Established:** G29 · **Findings-store id:** f6

## Summary
- [[MEM - Collision sector table 800A7E48]]: 223 records × `0x30`; each has an AABB + a `[+0x10]` pointer to 32-byte collision **plane** records (`~0x800D0xxx`).
- Built (scaled `<<5`) by converter [[FUNC_80030F60]] from the decompressed source region `0x800F7BF8`.
- Resolution chain: sector AABB select → per-frame candidate list `0x8009c230` (`[gp+0x57c]`) → resolver [[FUNC_800345CC]] → commit by [[FUNC_8003633C]] at `0x80036cec` → player Y `0x800a6504`.

## Evidence
- Live moving-player capture (JSON-RPC debugger) traced the full chain; sector-origin Y edits move Flik footing ~1:1 — see [[Finding - Collision RAM edit moves footing 1to1]].
- The "floor" is a set of planes, not a scalar — see [[Finding - Collision is planes not scalar]].

## Related functions
[[FUNC_8003633C]] · [[FUNC_800345CC]] · [[FUNC_80030F60]] · [[FUNC_8001A1DC]] (decompresses the source)

## Related memory structures
[[MEM - Collision sector table 800A7E48]] · [[MEM - Collision plane record]] · [[MEM - LEVEL.RAW chunk model]]

## Related experiments
[[Experiment - G29 collision lever validation]]

## Related fixtures / save states
[[Fixture - g30 openground]]

## DuckStation APIs used
[[API - readArray]] (all 223 in one call) · [[API - accessLog]] · [[API - addWatch]] · [[API - scatterWrite]]

## Next steps
On-disk source = chunk 32 ([[Finding - Collision on-disk source is chunk 32]]); a permanent disc edit needs the [[Finding - LEVEL.RAW is compressed|LZ codec]].

## Source
`src_re_geometry/geometry_g29_collision_source_plan.md`; findings-store f6
