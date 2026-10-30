---
kind: experiment
id: Experiment_-_G13_payload_v0
created: 2026-07-08
updated: 2026-07-08
status: legacy_imported
confidence: confirmed
legacy_source: ObsidianVault/Experiments/Experiment - G13 payload v0.md
aliases:
  - "Experiment - G13 payload v0"
---

# Experiment — G13 payload v0

> Migrated from `ObsidianVault/Experiments/Experiment - G13 payload v0.md` during the 2026-07-08 vault completion pass. Original action: `convert_to_experiment`. Reason: Experiment note should preserve proof artifacts and link Canon claims it validates.

# Experiment — G13 payload v0

> Directly deform mesh vertex 0 of the entry29 payload.

| Field | Value |
|-------|-------|
| Fixture / save state | operator boot of the built disc |
| Build image / tool | `ABL_G13_ENTRY29_PAYLOAD_V0_TEST.cue` via `tools/patch_g13_entry29_payload_v0_test.py` |
| Patch | entry29 v0.y `DAT 0x2f2fe` (s16) `-744` → `-232` (+512); build SHA1 `b6eecbab2f…` |
| APIs used | offline build + operator test + read-watch on the vertex |

## Goal
Edit vertex 0's Y in the payload and confirm via a read-watch that the engine reads it.

## Procedure (reproducible)
1. `tools/patch_g13_entry29_payload_v0_test.py` → patch `0x2f2fe`, rebuild.
2. Read-watch the **aligned** vertex base `0x8018faf4`; boot.

## Result
VALID BUILD / **vertex read CONFIRMED** at `0x8018faf4` (PC `0x80010928`, `lwc2`) / no obvious visual change. The inner s16 address `0x8018faf6` did **not** hit.

## Conclusion
**Lesson (reused by all later vertex experiments): watch the aligned `lwc2` base, not the inner s16.** Vertex 0 read but not visibly impactful → pick a command-stream-referenced silhouette vertex with a bigger delta (G14).

## Linked findings / functions / structures
- [[FUNC_80010000]] · [[MEM - fcn.80010000 mesh payload]]
## Source
`src_re_geometry/geometry_g11_payload_format.md` (§5.2)
