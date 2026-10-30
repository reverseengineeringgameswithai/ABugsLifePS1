---
kind: experiment
id: Experiment_-_G12_source_vec
created: 2026-07-08
updated: 2026-07-08
status: legacy_imported
confidence: confirmed
legacy_source: ObsidianVault/Experiments/Experiment - G12 source vec.md
aliases:
  - "Experiment - G12 source vec"
---

# Experiment — G12 source vec

> Migrated from `ObsidianVault/Experiments/Experiment - G12 source vec.md` during the 2026-07-08 vault completion pass. Original action: `convert_to_experiment`. Reason: Experiment note should preserve proof artifacts and link Canon claims it validates.

# Experiment — G12 source vec

> Translate a whole object by editing its source-record origin vector.

| Field | Value |
|-------|-------|
| Fixture / save state | operator boot of the built disc |
| Build image / tool | `ABL_G12_ENTRY29_VEC_TEST.cue` via `tools/patch_g12_entry29_source_vec_test.py` |
| Patch | entry29 source `vec[0]` `DAT 0x7388` `-10000` → `-8976` (+1024); patched DAT sha256 `f01c2a0a…`, build SHA1 `67b18e1a56…` |
| APIs used | offline build + operator test + CPU read confirmation |

## Goal
Move the entry29 object by shifting its source origin (the `vec[0]` field of the bit3 source record at runtime `0x80167b80`).

## Procedure (reproducible)
1. `tools/patch_g12_entry29_source_vec_test.py` → patch `0x7388`, rebuild.
2. Boot; read live `0x80167b80` to confirm the new value reached RAM.

## Result
VALID BUILD / PATCH LIVE / CPU READ CONFIRMED (`0x80167b80=FFFFDCF0`) / **no obvious visual change** (likely masked / off-screen object).

## Conclusion
Source-origin edits reach RAM but were visually silent for this object — pushed the investigation toward direct payload-vertex edits (G13/G14).

## Linked findings / functions / structures
- [[FUNC_8001EA6C]] · [[FUNC_80010000]] · [[MEM - fcn.80010000 mesh payload]]
## Source
`src_re_geometry/geometry_g11_payload_format.md` (§5.1)
