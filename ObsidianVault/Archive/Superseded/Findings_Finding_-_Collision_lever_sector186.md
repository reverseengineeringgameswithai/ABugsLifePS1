---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - Collision lever sector186.md
aliases:
  - "Finding - Collision lever sector186"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - Collision lever sector186.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_Collision_lever_sector186.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Finding - Collision lever sector186
type: finding
confidence: CONFIRMED
gstep: G30
tags: [finding, collision, lever]
---

# Finding — Localized collision lever = player sector sec186

> The single collision record to edit for a *local* floor change at the openground spot.

**Confidence:** CONFIRMED · **Established:** G30 R6 · **Findings-store id:** f12

## Summary
In [[Fixture - g30 openground]], Flik's sector = **sec186**, origin `(20608, 0, -40416)`, record at `0x800a7e48 + 186*0x30 = 0x800aa128`; the **Y lever is +4**. Lowering only sec186 by −3000 + jump dropped Flik −512 (partial — the resolver clamps to neighbors, so a full localized lower needs sec186 + adjacent sectors). Lowering all 223 sectors → Flik falls ~1:1.

## Evidence
[[API - readArray]] reads all 223 sector records (`base=0x800a7e48, count=223, stride=0x30`) in one call; targeted [[API - scatterWrite]] of sec186's Y produced the partial drop.

## Related functions
[[FUNC_8003633C]] · [[FUNC_800345CC]] · [[FUNC_80030F60]]

## Related memory structures
[[MEM - Collision sector table 800A7E48]] · [[MEM - Collision plane record]]

## Related experiments
[[Experiment - G29 collision lever validation]] · [[Experiment - G30 localized terrain edit]]

## Related fixtures / save states
[[Fixture - g30 openground]]

## DuckStation APIs used
[[API - readArray]] · [[API - scatterWrite]] · [[API - controller input]] · [[API - frame capture]]

## Next steps
A clean localized pit needs sec186 + adjacent sectors lowered together (and the matched visual edit).

## Source
`src_re_geometry/geometry_g30_terrain_render_source_plan.md` §18.2; findings-store f12
