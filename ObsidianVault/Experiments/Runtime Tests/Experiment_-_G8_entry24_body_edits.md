---
kind: experiment
id: Experiment_-_G8_entry24_body_edits
created: 2026-07-08
updated: 2026-07-08
status: legacy_imported
confidence: confirmed
legacy_source: ObsidianVault/Experiments/Experiment - G8 entry24 body edits.md
aliases:
  - "Experiment - G8 entry24 body edits"
---

# Experiment — G8 entry24 body edits

> Migrated from `ObsidianVault/Experiments/Experiment - G8 entry24 body edits.md` during the 2026-07-08 vault completion pass. Original action: `convert_to_experiment`. Reason: Experiment note should preserve proof artifacts and link Canon claims it validates.

# Experiment — G8 entry24 body edits

> Perturb the entry24 render-body row and observe (three builds).

| Field | Value |
|-------|-------|
| Fixture / save state | operator boot of each built disc |
| Build images / tools | `ABL_G8_ENTRY24_PLUS08_TEST` (`tools/patch_g8_entry24_plus08_test.py`), `..._PLUS08_A2_TEST` (`tools/patch_g8_entry24_plus08_a2_test.py`), `..._PLUS04_C_TEST` (`tools/patch_g8_entry24_plus04_c_test.py`) |
| Patches | `DAT+0x16ec` (+0x08, rt `0x80161ee4`): `9f fa`→`9f fb` (+256) / `9f fa`→`9f fe` (+1024); `DAT+0x16e8` (+0x04, rt `0x80161ee0`): `b3 f5`→`b3 f9` (+1024) |
| Build SHA1s | `67dbb83227…` (+256), `8714b578f2…` (+1024 A2), `9461ef48f9…` (C) |
| APIs used | offline build + operator test + CPU read confirmation; live RAM check `0x80161ee4` |

## Goal
After G7 found the entry24 body row (DAT `0x16e4/16e8/16ec/16f0`) is DAT-backed and read by the render path, edit those fields and look for a visible change.

> [!warning] BLOCKING GATE in `patch_g8_entry24_plus08_test.py`: verify the live value at `0x80161ee4` equals the static value before trusting the build (entry rows can be runtime-rewritten — G7 flagged `s3=0xfffd126d` ≠ static).

## Procedure (reproducible)
1. Confirm gate: live `0x80161ee4` == static (`+0x08` passed: live==static).
2. Build with the relevant `patch_g8_*` tool → `rebuild_with_patched_dat.py`.
3. Boot; compare ground/terrain to pristine.

## Result
All three: VALID BUILD / CPU READ CONFIRMED (A2 live RAM `0x80161ee4=FFFFFE9F`) / **no obvious visual change**.

## Conclusion
entry24's body row is read but visually inert — low yield. G9 then showed entry24 is a *culling/range* row, not a mesh-position row, which explains the silence.

## Linked findings / functions / structures
- [[Finding - entry24 is a culling row]]
- [[FUNC_800140A0]] · [[MEM - Trail and pass3 tables]]
## Source
`src_re_geometry/geometry_g55_dynamic_watch.md` (§11), `src_re_geometry/geometry_g9_entry24_dataflow.md`
