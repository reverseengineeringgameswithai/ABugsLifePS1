---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Physics/Physics.md
aliases:
  - "Physics"
migration_action: convert_to_canon
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Physics/Physics.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Physics.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Physics
type: hub
tags: [hub, physics, collision]
---

# Physics — Map of Content

> Movement integration, floor/collision response, and pickup-proximity contact. Closely tied to [[Collision]].

## Movement + collision response
[[FUNC_8003633C]] is the per-frame movement + collision integrator: it sweeps (`fcn.80035f24`), resolves against collision planes ([[FUNC_800345CC]]), and commits the corrected player Y (`0x80036cec`). The floor is a set of planes, resolved as a swept plane-distance clamp + skin (`−0xc0`). See [[Finding - Player Y writer FUNC_3633C]] · [[Finding - Collision is planes not scalar]].

## Pickup proximity (distinct from world collision)
[[FUNC_800586B0]] (contact walker) tests Flik against the 64-slot [[MEM - Contact array 800B0D18]] with **weak-Y** distance math (Y weighted ⅓) → the auto-collect "height band" rule. This is *pickup proximity*, NOT floor collision.

## Levers
- Footing: edit the [[MEM - Collision sector table 800A7E48|sector origin Y]] → moves ~1:1 ([[Finding - Collision RAM edit moves footing 1to1]] · [[Finding - Collision lever sector186]]).
- Pickup reach: keep final runtime Y ≳ −21000 (weak-Y) — see [[Finding - Type-0x3f pickups are coordinate-moddable]].

## Related
- Functions: [[FUNC_8003633C]] · [[FUNC_800345CC]] · [[FUNC_800586B0]] · [[FUNC_80025084]]
- Structures: [[MEM - Player state 800A6500]] · [[MEM - Collision plane record]]
- Experiments: [[Experiment - G29 collision lever validation]]
- Hubs: [[Collision]] · [[Camera]]
