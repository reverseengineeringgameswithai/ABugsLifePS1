---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Functions/FUNC_8003633C.md
aliases: []
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Functions/FUNC_8003633C.md`
- Replacement/current location: `ObsidianVault/Canon/Functions/FUNC_8003633C_player_movement_+_collision_integrator.md`
- Archive reason: Existing function note; migrate only evidence-backed claims and link C source where available.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: FUNC_8003633C — player movement + collision integrator
type: function
address: 0x8003633C
confidence: CONFIRMED
tags: [function, collision, physics, g29]
---
# FUNC_8003633C — per-frame movement + collision-response integrator (player-Y writer)

> Resolves and **commits Flik's floor-corrected Y** each frame. The actual player-Y writer (supersedes the earlier `fcn.8005b134` guess).

| Field | Value |
|-------|-------|
| Address | 0x8003633C |
| Source file | `geometry_collision_consumers.c` / `geometry_runtime_buffers.c` (G29) |
| Confidence | CONFIRMED (G29 runtime WRITE-watch) |

## Purpose
Per-frame movement + collision integrator on a position struct (`a0`). For the player (`a0 = 0x800a6500`) it commits the collision-resolved Y to `0x800a6504` at **`0x80036cec`** (the decisive store, reading `[sp+0x1c]`). Reusable over any XYZ vector (also caught with a stack vector). Probe-bias stores `±0xc80` at `0x80036380 / 0x80036d54`; free-velocity integ `0x80036d30`.

## Arguments / Returns
`a0/s7` = position struct base (player `0x800a6500`); `a1/s5` = velocity/delta vec (`0x800a652c`); `a2` = contact-flag bytes (`0x800a6582`). Writes resolved Y.

## Calls (callees)
- `fcn.80035f24` — collision sweep → per-axis deltas (sp+0x10).
- [[FUNC_800345CC]] — resolve/accumulate → result.
- `fcn.80035280` — alt collision path.

## Called by (callers)
- `0x800495c8` (RA `0x800495d0`, observed), `0x8004c024`, `0x8004e628`.

## Globals & structures touched
- [[MEM - Player state 800A6500]] · [[MEM - Collision sector table 800A7E48]] · [[MEM - Collision plane record]] · candidate list `0x8009c230`, output list `0x80090868`.

## Evidence & confidence notes
G29 WRITE-watch on `0x800a6504` while moving Flik pinned the writer to `0x80036cec` here; a jal-caller scan found the three callers. This **supersedes** the static-era claim that [[FUNC_8005B134]] was the sole writer (it has 0 jal callers). Footing scales ~1:1 with a sector-origin edit — see [[Finding - Collision RAM edit moves footing 1to1]].

## Related
- Findings: [[Finding - Player Y writer FUNC_3633C]] · [[Finding - Collision sector table]] · [[Finding - Collision is planes not scalar]] · [[Finding - Visual is not collision]]
- Functions: [[FUNC_800345CC]] · [[FUNC_80030F60]] · [[FUNC_8005B134]] · [[FUNC_8001A1DC]]
- Experiments: [[Experiment - G29 collision lever validation]] · Fixture: [[Fixture - g30 openground]]
- Source docs: `src_re_geometry/geometry_g29_collision_source_plan.md`
