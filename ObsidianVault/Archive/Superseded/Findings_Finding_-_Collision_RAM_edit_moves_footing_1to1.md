---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - Collision RAM edit moves footing 1to1.md
aliases:
  - "Finding - Collision RAM edit moves footing 1to1"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - Collision RAM edit moves footing 1to1.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_Collision_RAM_edit_moves_footing_1to1.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Finding - Collision RAM edit moves footing 1to1
type: finding
confidence: CONFIRMED
gstep: G29
tags: [finding, collision, lever]
---

# Finding — A collision RAM edit moves Flik's footing ~1:1

> The decisive causal proof that the sector table *is* the floor: change a sector origin Y in RAM and Flik's resting Y tracks it 1:1.

**Confidence:** CONFIRMED · **Established:** G29

## Summary
Editing a sector origin Y (e.g. sector-104 record `0x800A91C8+4`) via live RAM/[[API - scatterWrite]] moves Flik's footing ~1:1: end **X stays constant**, end **Y scales** with the edit. A large enough lower crosses a kill-plane (≈ ≤8000) and Flik falls out. No disc build — pure live edit.

## Evidence
Tested deltas +8192 / +16384 / −8192 / −3000 against player Y `0x800a6504` after settling + a jump; endY scaled, endX unchanged. Confirms the LEVEL.RAW-sourced sector table is the collision floor lever, independent of the visual mesh ([[Finding - Visual is not collision]]).

## Related functions
[[FUNC_8003633C]] · [[FUNC_800345CC]] · [[FUNC_80030F60]]

## Related memory structures
[[MEM - Collision sector table 800A7E48]]

## Related experiments
[[Experiment - G29 collision lever validation]]

## Related fixtures / save states
[[Fixture - g30 openground]]

## DuckStation APIs used
[[API - scatterWrite]] · [[API - readArray]] · [[API - addWatch]] · [[API - controller input]] · [[API - frame capture]] · [[API - experiment runner]]

## Next steps
Combine with the matched visual lever for a photogenic pit (rendering-limited — see [[Finding - Localized terrain edit]]).

## Source
`src_re_geometry/geometry_g29_collision_source_plan.md`
