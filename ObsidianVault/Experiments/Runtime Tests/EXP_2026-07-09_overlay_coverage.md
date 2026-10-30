---
kind: experiment
id: EXP_2026-07-09_overlay_coverage
aliases: [EXP_2026-07-09_overlay_coverage]
name: Per-overlay dynamic coverage (OVL o1)
status: success
confidence: confirmed
source_state: evidence
validates: [SYS_overlays_and_runtime_loading, SYS_menu_and_frontend, SYS_function_census]
artifacts: [tools/trace_overlay_coverage.py, analysis/traces/overlay_coverage.json, analysis/overlay_naming_priority.json]
---

# EXP_2026-07-09_overlay_coverage

## Question
Which OVERLAY functions actually execute at runtime? Overlays are the biggest un-understood code mass
(168/192 fns unnamed), and naming them needs a runtime signal the resident `trace_level_coverage.py` never
captures (it watches only `[0x80010000,0x80082800)`).

## Method (pristine media only)
`tools/trace_overlay_coverage.py` replays each pristine cold-boot movie in `movies/go_to_end/` on a
**reproducible** instance (`launch_repro_playback.sh` — a from-boot movie desyncs without the recorded
`[CPU] CachedInterpreter` mode + card seed) and installs a `movie.coverageToFrame` range watch over the
overlay window `[0x800B39A0,0x800BE000)`. Region-B PCs → MEMORY; Region-A PCs → the level's `_LEVEL`/`_LEVEL1`
variant via census fn-starts. **No modded saves** (the [[SYS_modding_safety]] EXE-code gate constraint);
throwaway instance, operator port 2346 untouched.

## Findings (all 16 movies, `reproducible=true`)
- **150 covered overlay functions across 20 overlays.** Proof run: LEVEL01 captured 5,922 distinct overlay PCs.
- **MEMORY.BIN: 44/69 functions execute** — the boot→title→menu→save path runs at the start of *every* movie,
  so a single movie already exercises most of the front-end. This is the naming target for [[SYS_menu_and_frontend]].
- **LEVEL01–10:** each level's `_LEVEL`/`_LEVEL1` variants covered (2–8 fns each).
- **LEVEL11–15 resolved:** they execute Region-A code (588–1,189 PCs) but map to **no censused overlay** —
  `OVL/` holds only LEVEL00–10 blobs, so LEVEL11–15 load **unextracted** overlay blobs (a scoped
  disc-extraction sub-task, out of scope for the LEVEL01–10 naming rollout).
- `overlay_naming_priority.py`: 148 unnamed overlay fns ranked, **118 dynamic-covered**.

## Links
[[SYS_overlays_and_runtime_loading]] · [[SYS_function_census]] · [[DuckStation_API_Index]] · [[Consistency Audit]].
