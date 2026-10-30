---
kind: experiment
id: Experiment_-_G14_payload_vertex_grass
created: 2026-07-08
updated: 2026-07-08
status: legacy_imported
confidence: confirmed
legacy_source: ObsidianVault/Experiments/Experiment - G14 payload vertex grass.md
aliases:
  - "Experiment - G14 payload vertex grass"
---

# Experiment — G14 payload vertex (grass)

> Migrated from `ObsidianVault/Experiments/Experiment - G14 payload vertex grass.md` during the 2026-07-08 vault completion pass. Original action: `convert_to_experiment`. Reason: Experiment note should preserve proof artifacts and link Canon claims it validates.

# Experiment — G14 payload vertex (grass)

> First confirmed **visible** payload-vertex edit — deform a command-stream-referenced silhouette vertex.

| Field | Value |
|-------|-------|
| Fixture / save state | operator boot of the built disc |
| Build image / tool | `ABL_G14_ENTRY29_PAYLOAD_VERTEX_TEST.cue` via `tools/patch_g14_entry29_payload_vertex_test.py` |
| Patch | entry29 v14.y `DAT 0x2f3a6` (s16) `-1601` → `-2625` (-1024); build SHA1 `53608e21ed…` |
| APIs used | command-stream decode (`0x2f494..0x2f59c`) + offline build + operator test |

## Goal
Pick a vertex actually referenced by the primitive command stream (a visible silhouette vertex) and apply a large Y delta.

## Procedure (reproducible)
1. Decode entry29's command stream (`0x2f494..0x2f59c`) to find a referenced near-apex vertex (v14).
2. `tools/patch_g14_entry29_payload_vertex_test.py` → patch `0x2f3a6`, rebuild.
3. Boot; observe.

## Result
VALID BUILD / vertex read CONFIRMED / **VISIBLE RENDER CHANGE** — the object visibly deforms. The object turns out to be **grass/decor (non-tangible)**, not floor.

## Conclusion
The payload-vertex edit method is proven end-to-end (edit → build → visible deform). Now need to find a *terrain/floor* payload rather than decor → G15/G16/G17.

## Linked findings / functions / structures
- [[Finding - Payload vertex edits are visible]]
- [[FUNC_80010000]] · [[FUNC_8001EA6C]] · [[MEM - fcn.80010000 mesh payload]]
## Source
`src_re_geometry/geometry_g11_payload_format.md` (§5.3)
