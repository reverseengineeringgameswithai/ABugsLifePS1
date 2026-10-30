---
kind: campaign
id: collision_floor_planes
phase: 4
family: movement_world_physics
rows: [E02_collision]
status: completed
created: 2026-07-15
updated: 2026-07-15
---

# Game Solving Campaign - Collision and Floor Planes

## Binding scope

This child campaign owns E02 only: load-time sector conversion and grid,
player candidate construction, typed collision plane semantics, swept response,
resolved player/floor/ground state, region-code query, capacity and lifecycle.

It does not own visible terrain (E01), camera behavior (E04), mover policy
(E08), hazard/damage behavior (E10), stage objectives or transition dispatch.
Those rows consume E02 interfaces without changing this campaign's boundary.

## Evidence matrix

| Required dimension | Reproduced evidence |
|---|---|
| Oracle | Pinned retail executable; hash-verified pristine mounted media; inspected pristine saves; cold-boot pre-edit equality |
| Frontier | 13 byte-matched regions, 19 decisive opcodes, typed sector/plane/candidate structures and the unguarded candidate capacity boundary |
| Lifecycle | Pause/resume, candidate scratch reset, native death/respawn and exact LEVEL01→LEVEL02→LEVEL01 table replacement |
| Controls | Active origin and plane-reference positives; distant-sector, neutral, pause and region-gate negatives |
| Breadth | Full tables for Training, stages 1–15 and all bonuses; region codes 1–4; floor/slope and other plane orientations |
| Dependencies | Untruncated player integrator, swept resolver, Y commit and region-query execution evidence |
| Source | Pinned executable hashes; 24 classified RAW inputs; all 28 collision marker chunks semantically round-tripped |
| Residuals | Flight ordinary-player bypass retained; render/camera/mover/hazard/objective/transition owners explicitly bounded |
| Exit gate | Natural LEVEL01 sector 177/code 2, transition lever 1, native gate-1 result 2 and gate-0 result 0 |

Machine authority is `config/phase4_collision.yaml` plus
`analysis/phase4_collision.json` (SHA-256
`d1987d886559928ba48ba8dae9c97157ad25fdec3c9233311b427fba8cdf9399`).
The finding guard is
`tests/test_phase4_collision.py::test_retained_collision_evidence_recomputes_low_level_predicates`.

## Capacity and failure behavior

The sector-grid scan bound is 700. Candidate pointers occupy the 400-slot span
ending at the adjacent pool `0x8009C870`, while the original append at
`0x800368E8` has no bounds check. Any future geometry generator must reject a
candidate upper bound of 400 or greater; passing ordinary examples is not a
substitute for this guard.

## Closure decision

The row is solved because the static and asset sources, runtime structures,
positive and negative causal controls, all-stage breadth, lifecycle, execution
ownership and region/exit behavior are directly reproduced. No open residual
intersects E02 itself. Downstream consumer behavior stays open under its own
row and does not hold E02 open.

Promoted truth: [[SYS_collision_and_floor_planes]]. Runtime history and failed
hypotheses: [[EXP_2026-07-15_phase4_collision_and_floor_planes]].
