---
kind: experiment
id: Experiment_-_G28_Candidate_A_floor_Y
created: 2026-07-08
updated: 2026-07-08
status: legacy_imported
confidence: confirmed
legacy_source: ObsidianVault/Experiments/Experiment - G28 Candidate A floor Y.md
aliases:
  - "Experiment - G28 Candidate A floor Y"
---

# Experiment — G28 Candidate A floor Y

> Migrated from `ObsidianVault/Experiments/Experiment - G28 Candidate A floor Y.md` during the 2026-07-08 vault completion pass. Original action: `convert_to_experiment`. Reason: Experiment note should preserve proof artifacts and link Canon claims it validates.

# Experiment — G28 Candidate A floor Y

> Build-and-operator-test the count-validated floor payload — the experiment that proved **visual ≠ collision**.

| Field | Value |
|-------|-------|
| Fixture / save state | operator boot of the built disc (visible-floor view) |
| Build image / tool | `ABL_G28_CANDIDATE_A_FLOOR_Y_TEST.cue` via `tools/patch_g28_candidate_a_floor_y_test.py` |
| Patch | Candidate A v16.y `DAT 0x18992` `89 13` → `89 17` (s16 5001→6025, +1024) |
| SHA1 | pristine `b376cb506f437a1cda721fd13766ddbca7c6a247`; patched/built `a1cf8d8e638460b4861f4d405872bff0a2738f5f` |
| APIs used | READ-watch + EXEC `0x80010718` (SXY) for projection proof; offline build + operator visual test |

## Goal
Confirm Candidate A (DAT `0x188cc`, runtime `0x801790c4`, 83 verts, flatness 0.154, world-space, unique) reaches render/projection, then visually deform it and check whether collision follows.

## Procedure (reproducible)
1. READ-watch vertex base `0x801790c8` → hit (ra `0x800206a0`, count 83) confirms it's a live [[FUNC_80010000]] payload.
2. EXEC `0x80010718` → capture SXY (prim1 `0x007A0164/00730182/007B0180`, prim2 `0x007F01A8/...`) → screen Y≈115–133, central/lower band → projection confirmed.
3. `tools/patch_g28_candidate_a_floor_y_test.py` (checks pristine sha1) → patch `0x18992` → `rebuild_with_patched_dat.py`.
4. Boot; walk Flik over the projected area.

## Result
VALID DAT-BACKED / RUNTIME READ CONFIRMED / PROJECTION CONFIRMED → built and operator-tested: **VISIBLE TERRAIN DEFORMATION** (terrain caves inward, angle-dependent) in Candidate A's projected area; Flik and objects still render; **collision did NOT follow** (Flik still walks the original footing).

## Conclusion
Candidate A = **CONFIRMED DAT-backed VISUAL terrain/floor render payload**. The visual terrain payload is **not** the collision/pathing source — this kicks off the collision-source hunt (G29).

## Linked findings / functions / structures
- [[Finding - Candidate A is DAT-backed visual terrain]] · [[Finding - Visible ground from DAT verts]] · [[Finding - Visual is not collision]]
- [[FUNC_80010000]] · [[FUNC_80019934]] · [[MEM - fcn.80010000 mesh payload]]
- Fixture for re-observation: [[Fixture - g30 openfloor]]
## Source
`src_re_geometry/geometry_g28_candidate_a_runtime_confirmation.md`
