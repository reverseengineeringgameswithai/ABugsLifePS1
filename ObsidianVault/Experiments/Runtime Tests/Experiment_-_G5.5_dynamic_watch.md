---
kind: experiment
id: Experiment_-_G5.5_dynamic_watch
created: 2026-07-08
updated: 2026-07-08
status: legacy_imported
confidence: confirmed
legacy_source: ObsidianVault/Experiments/Experiment - G5.5 dynamic watch.md
aliases:
  - "Experiment - G5.5 dynamic watch"
---

# Experiment — G5.5 dynamic watch

> Migrated from `ObsidianVault/Experiments/Experiment - G5.5 dynamic watch.md` during the 2026-07-08 vault completion pass. Original action: `convert_to_experiment`. Reason: Experiment note should preserve proof artifacts and link Canon claims it validates.

# Experiment — G5.5 dynamic watch

> Dynamically prove a parser-geometry field is read at runtime and identify the reader.

| Field | Value |
|-------|-------|
| Fixture / save state | pristine `Disney-Pixar A Bug's Life (v1.0).cue` (no save state) |
| Build image / tool | none (read-only observation) |
| Patch | none |
| APIs used | DuckStation GUI debugger read/data + execute breakpoints; live RAM via `/proc/<pid>/mem` (see [[Finding - Live RAM probe via proc mem]]) |

## Goal
Confirm that the parser-produced geometry tables are actually consumed by the render path, and pin the consuming function/PC.

## Procedure (reproducible)
1. Boot LEVEL01; via `/proc/<pid>/mem` confirm live globals: `[0x80082498]=0x801607f8` (DATbase), `[0x800822f0]=624`, `[0x800824ac]=0x80161cfc` (trail), `[0x80082508]=0x801642e4` (pass-3).
2. Set execute breakpoints on the render-driver GTE helpers; confirm [[FUNC_800140A0]] (a0=`0x80161cfc`), `fcn.80014360` (a0=`0x801642e4`), `fcn.800146e0` all run.
3. Set read/data breakpoints on trail entry flag halfwords `0x80161d0a` (DAT `0x1512`) and `0x80161d1e` (DAT `0x1526`).

## Result
- Read watches on the originally-chosen record s0=`0x4e00` (output rec 261) → **no hits** (unsuitable, zero-hit body).
- Read watches on `0x80161d0a` / `0x80161d1e` → **HIT** inside [[FUNC_800140A0]] at read site `0x80014170` (`lh t3,0x0e(a0)`).

## Conclusion
The render stage reads DAT-backed pass-1 *trail* flag/sentinel halfwords. The chosen s0=0x4e00 record is not on the active render path. Sets up [[Experiment - G6 render sentinel]].

## Linked findings / functions / structures
- [[Finding - Trail flag gates terrain render]] · [[Finding - Live RAM probe via proc mem]]
- [[FUNC_800140A0]] · [[FUNC_800224EC]] · [[MEM - Trail and pass3 tables]]
## Source
`src_re_geometry/geometry_g55_dynamic_watch.md`
