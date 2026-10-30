---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Collision/Collision.md
aliases:
  - "Collision"
migration_action: split
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Collision/Collision.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Collision.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Collision
type: hub
tags: [hub, collision, physics]
---

# Collision — Map of Content

> How Flik's footing is computed. Discovered in G29: the floor is a set of **planes** sourced from LEVEL.RAW chunk 32, entirely separate from the visual mesh.

## Chain (disk → player Y)
LEVEL.RAW chunk 32 → [[FUNC_8001A1DC]] decompress → src `0x800F7BF8` → [[FUNC_80030F60]] builds [[MEM - Collision sector table 800A7E48]] (`<<5`) → sector AABB select → candidate list `0x8009c230` → [[FUNC_800345CC]] resolve (swept plane clamp + skin) → [[FUNC_8003633C]] commit at `0x80036cec` → player Y `0x800a6504`.

## Confirmed findings
- [[Finding - Collision sector table]] · [[Finding - Collision on-disk source is chunk 32]]
- [[Finding - Collision is planes not scalar]] · [[Finding - Collision RAM edit moves footing 1to1]]
- [[Finding - Collision lever sector186]] · [[Finding - Player Y writer FUNC_3633C]]
- [[Finding - No static collision consumer]] (why static scans missed it) · [[Finding - Visual is not collision]]

## Key functions
[[FUNC_8003633C]] · [[FUNC_800345CC]] · [[FUNC_80030F60]] · [[FUNC_8001A1DC]] · [[FUNC_80025084]] (wall/ledge candidate) · [[FUNC_8005B134]] (superseded claim)

## Structures
[[MEM - Collision sector table 800A7E48]] · [[MEM - Collision plane record]] · [[MEM - Player state 800A6500]] · [[MEM - LEVEL.RAW chunk model]]

## Experiments / fixtures
[[Experiment - G29 collision lever validation]] · [[Fixture - g30 openground]]

## Playbooks
[[Playbook - Trace collision resolution]] · [[Playbook - Correlate rendering and collision]]

## Open questions
Per-plane `refpt.y` lever (winning-record capture was buggy); `fcn.8005b134` ↔ `fcn.8003633c` relationship; permanent disc edit blocked by the [[Finding - LEVEL.RAW is compressed|LZ codec]]. See [[Open Questions]].

## Source docs
`src_re_geometry/geometry_g29_collision_source_plan.md`, `geometry_collision_consumers.c`.
