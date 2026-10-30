---
kind: experiment
id: Experiment_-_G16_emitted_payload_vertex_wall
created: 2026-07-08
updated: 2026-07-08
status: legacy_imported
confidence: confirmed
legacy_source: ObsidianVault/Experiments/Experiment - G16 emitted payload vertex wall.md
aliases:
  - "Experiment - G16 emitted payload vertex wall"
---

# Experiment — G16 emitted payload vertex (wall)

> Migrated from `ObsidianVault/Experiments/Experiment - G16 emitted payload vertex wall.md` during the 2026-07-08 vault completion pass. Original action: `convert_to_experiment`. Reason: Experiment note should preserve proof artifacts and link Canon claims it validates.

# Experiment — G16 emitted payload vertex (wall)

> Pick an **emitted, on-screen** vertex (proven by the packet-store gate) and deform it.

| Field | Value |
|-------|-------|
| Fixture / save state | operator boot of the built disc |
| Build image / tool | `ABL_G16_EMITTED_PAYLOAD_VERTEX_TEST.cue` via `tools/patch_g16_emitted_payload_vertex_test.py` |
| Patch | payload `0x356bc` (e128, rt `0x80195eb4`) v10.y `DAT 0x3573a` (s16) `6841` → `5817` (-1024); build SHA1 `4c638f61c1…` |
| APIs used | static project→reject→pack decode; runtime EXEC at packet-store gate `0x800108b4`; offline build + operator test |

## Goal
Only edit a vertex that actually reaches the packet-store (emitted) — emit-in-view is necessary, not just a read.

## Procedure (reproducible)
1. EXEC-watch the packet-store gate `0x800108b4` (where `addi s3,s3,0x34` advances the OT packet). At that PC, `a0` = vertex base ⇒ payload = `a0-4`. (t5/t6/t7 there are reused packet words — read `s3` packet or BP the SXY site `0x80010718`.)
2. Identify emitted payload `0x356bc`; patch v10.y at `0x3573a`; rebuild.
3. Boot; observe.

## Result
VALID BUILD / **emitted payload CONFIRMED** / **VISIBLE WALL RENDER CHANGE**. Payload `0x356bc` is reclassified as a **wall / vertical face** (flatness 0.48, Y-band 1354), NOT floor.

## Conclusion
Emit-in-view is necessary but **not sufficient** to be "floor" — a deformable, emitted, fairly-flat payload can still be a wall. Need flat + tight-Y + lower-center screen → G17/G27.

## Linked findings / functions / structures
- [[Finding - 0x356bc is a wall not floor]] · [[Finding - Payload vertex edits are visible]]
- [[FUNC_80010000]] · [[MEM - fcn.80010000 mesh payload]]
## Source
`src_re_geometry/geometry_g16_screen_space_vertex_selection.md`
