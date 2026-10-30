---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Hypotheses/HYP - visual equals collision.md
aliases:
  - "HYP - visual equals collision"
migration_action: needs_review
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Hypotheses/HYP - visual equals collision.md`
- Archive reason: Planning/blocker/hypothesis material is not Canon unless evidence-backed claims are extracted.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: HYP - visual equals collision
type: hypothesis
status: DISPROVEN
confidence: CONFIRMED-false
tags: [hypothesis, collision, rendering]
---

# HYP — "editing the visible floor moves the collision floor"

> [!warning] Archived wrong hypothesis
> This disproven hypothesis is represented in the revamped Archive as [[WHYPE_visible_floor_equals_collision]]. Current Canon is [[SYS_render_collision_source_separation]].

> The natural starting assumption — that the geometry you see is the geometry you stand on. **DISPROVEN.** They are separate layers.

| Field | Value |
|-------|-------|
| **Statement** | Editing the visible terrain/floor mesh will move where Flik can stand (visual == collision). |
| **Status** | **DISPROVEN** |
| **Confidence** | high (operator-tested + traced) |

## Supporting evidence (before)
- Intuition: most simple games share one mesh for render + collision.
- Early G-work edited render-side fields hoping footing would follow.

## Contradicting evidence (decisive)
- **G28**: a built DAT edit to the visible terrain payload (Candidate A v16.y) visibly deformed the ground, but **Flik kept walking on the original surface** — collision did not follow. → [[Experiment - G28 Candidate A floor Y]]
- **G29**: the player-Y writer [[FUNC_8003633C]] resolves footing from the [[MEM - Collision sector table 800A7E48|sector table]] / [[MEM - Collision plane record|plane records]] (LEVEL.RAW **chunk 32**), a *different* file from the visible mesh (LEVEL.DAT via `fcn.80010000` — the visible floor; the chunk-35 mesh is the occluded layer).
- **G6**: removing terrain *render* (trail flag) left collision intact. → [[Finding - Trail flag gates terrain render]]

## Experiments
- Completed: [[Experiment - G28 Candidate A floor Y]] · [[Experiment - G29 collision lever validation]] · [[Experiment - G6 render sentinel]]
- A *matched* edit (both layers) lands Flik coincident on the lowered floor — consistency proven (G30 R6).

## Conclusion
→ promoted to [[Finding - Visual is not collision]]. To change the floor you must edit **both** the visual source ([[MEM - Terrain vertex buffer 8012C1D0]] / Candidate A) and the collision source ([[MEM - Collision sector table 800A7E48]]).

## See also
[[Hypotheses]] · [[Finding - Visual is not collision]] · [[Collision]] · [[Rendering]]
