---
kind: experiment
id: Experiment_-_G15_runtime_payload_vertex
created: 2026-07-08
updated: 2026-07-08
status: legacy_imported
confidence: confirmed
legacy_source: ObsidianVault/Experiments/Experiment - G15 runtime payload vertex.md
aliases:
  - "Experiment - G15 runtime payload vertex"
---

# Experiment — G15 runtime payload vertex

> Migrated from `ObsidianVault/Experiments/Experiment - G15 runtime payload vertex.md` during the 2026-07-08 vault completion pass. Original action: `convert_to_experiment`. Reason: Experiment note should preserve proof artifacts and link Canon claims it validates.

# Experiment — G15 runtime payload vertex

> Test a flatness-selected terrain candidate payload (read ≠ drawn lesson).

| Field | Value |
|-------|-------|
| Fixture / save state | operator boot of the built disc |
| Build image / tool | `ABL_G15_RUNTIME_PAYLOAD_VERTEX_TEST.cue` via `tools/patch_g15_runtime_payload_vertex_test.py` |
| Patch | payload `0x10180` (rt `0x80170978`) v46.y `DAT 0x103ae` (s16) `7302` → `6278` (-1024); build SHA1 `fbdb3ba9a3…` |
| APIs used | static survey `tools/survey_level01_payloads.py` (flatness = Yspread/max(Xspread,Zspread)); runtime EXEC `0x80010000` a0-log; offline build + operator test |

## Goal
Use a flatness metric to pick a unique (non-instanced) terrain-like payload and edit a vertex.

## Procedure (reproducible)
1. `tools/survey_level01_payloads.py` → shortlist flat payloads; reject the static "primary" `0x8018c234` (instanced ×6).
2. Pick `0x80170978` (unique, flatness 0.30); patch v46.y at `0x103ae`; rebuild.
3. Read-watch the vertex; boot.

## Result
VALID BUILD / read CONFIRMED (`0x80170ba4`, PC `0x8001069c`) / **no visual change** — the watch fired at the `lwc2` load *before* the reject/clip tests, so the vertex was read but the primitive was never emitted.

## Conclusion
**Read ≠ drawn.** Need screen-space (emitted-primitive) evidence, not just a read-watch → G16.

## Linked findings / functions / structures
- [[FUNC_80010000]] · [[MEM - fcn.80010000 mesh payload]]
## Source
`src_re_geometry/geometry_g15_terrain_payload_candidates.md`
