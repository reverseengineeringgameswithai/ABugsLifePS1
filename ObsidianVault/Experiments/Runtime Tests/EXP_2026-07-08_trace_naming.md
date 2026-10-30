---
kind: experiment
id: EXP_2026-07-08_trace_naming
name: Per-level dynamic coverage + trace-based function naming (Phase 5)
status: success
confidence: confirmed
source_state: evidence
validates: [SYS_function_census, SYS_decomp_substrate, SYS_re_evidence_policy]
fixtures: [from-boot-movie-LEVEL00-Training, from-boot-movie-LEVEL01, from-boot-movie-LEVEL02, from-boot-movie-LEVEL03, from-boot-movie-LEVEL04, from-boot-movie-LEVEL05, from-boot-movie-LEVEL06, from-boot-movie-LEVEL07, from-boot-movie-LEVEL08, from-boot-movie-LEVEL09, from-boot-movie-LEVEL10, from-boot-movie-LEVEL11, from-boot-movie-LEVEL12, from-boot-movie-LEVEL13, from-boot-movie-LEVEL14, from-boot-movie-LEVEL15]
artifacts: [tools/trace_level_coverage.py, tools/launch_repro_playback.sh, tools/apply_symbol_names.py, analysis/traces/level_coverage.json, analysis/naming_priority.json, analysis/naming/phase5_trace_names.json]
---

# EXP_2026-07-08_trace_naming

## Question
Which of the ~642 unknown resident functions actually EXECUTE in the game, in
which levels, and how many can be named with existing evidence — feeding the
`dynamic` census signal, the ranker, and the symbol map?

## Method
1. **Coverage sweep.** Replay each of the 16 cold-boot movies in
   `movies/go_to_end/` under `movie.coverageToFrame` (now cycle-neutral — see
   [[EXP_2026-07-08_coverageToFrame_cycle_neutrality]]) via
   `tools/trace_level_coverage.py --relaunch --fresh`. A fresh repro instance is
   launched per movie by `tools/launch_repro_playback.sh` (config matched to the
   recording environment: `[CPU] ExecutionMode=CachedInterpreter`, region auto,
   overclock off, analog pad; memory card seeded from a pristine snapshot). Each
   returned resident-text PC maps to its containing census function.
2. **Quality gate.** Coverage is trusted only when the replay is
   `reproducible=true` AND reached (near) the final frame AND settled in a
   nonzero gameplay `current_scene_id` (`0x80082504`). Observed scene per level
   is recorded — it forms the empirical scene→level table below.
3. **Fold + prioritize.** `tools/function_census.py` unions the
   `function_levels` keys into the `dynamic` discovery set (→
   `confidence: confirmed`); `tools/naming_priority.py` ranks the remaining
   unknowns by `100·dynamic + 8·levels + 3·callers + callees`.
4. **Name.** Harvest addresses already tied to a role by existing documented RE
   (`src_re/*.c`, `ObsidianVault/Canon/*`, auto-memory), merge/dedup (precedence
   Canon > src_re > memory; highest tier; evidence unioned), filter to nameable
   resident starts, and apply via `tools/apply_symbol_names.py` (validated,
   append-only into `symbols/re_symbols.sym`). A small second batch adds
   call-graph-inferred names where named neighbours make the role unambiguous.

## Results
- **16/16 movies trusted** (`desynced: []`). Coverage: **765 resident functions
  executed across the 15 numbered levels + Training**, 495 of them previously
  `classification=unknown`.
- **Dynamic-tagged resident functions: 8 → 746.**
- **Named resident functions: 399 → 502** (**103 new names**: 83 proven, 20
  inferred; 26 were `FUNC_` placeholder upgrades, so 0 placeholders remain).
- **Match metric UNCHANGED at 86 / 8.05%** — dynamic coverage is evidence, never
  a match (guard in `tools/function_census.py::_write_progress`).

### Empirical scene → level table (`current_scene_id` at 0x80082504)
| Training | L1 | L2 | L3 | L4 | L5 | L6 | L7 | L8 | L9 | L10 | L11 | L12 | L13 | L14 | L15 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0x11 | 0x1 | 0x3 | 0x2 | 0x6 | 0xa | 0xb | 0x4 | 0x5 | 0xe | 0x7 | 0xc | 0xd | 0x9 | 0x8 | 0xf |

All 16 scenes are distinct — a full-coverage sanity check that every movie
reached its own level.

## Naming convention (three-tier, evidence-required)
- **proven** — dynamic hit + a byte-match / PsyQ signature / prior confirmed
  behavior note; `confidence: confirmed`.
- **inferred** — role deduced from call-graph position or callee signatures;
  `confidence: high|medium`.
- **temporary** — `FUNC_<addr>` placeholder; not renamed without evidence.

Names enter the system ONLY through `symbols/re_symbols.sym` (authoritative);
`function_census.py` propagates them into `analysis/functions.json`. Per-name
address, tier, evidence and rationale are recorded in
`analysis/naming/phase5_trace_names.json` (the applied manifest) — the single
source of truth, not duplicated per Canon note.

## Caveats
- **LEVEL07 re-recorded.** The first LEVEL07 movie was a bad recording — it
  desynced even on the operator's own DuckStation and drifted into scene `0xc`
  (LEVEL11's scene). It was quarantined, the operator re-recorded it, and the
  new take replays clean (scene `0x4`, the one previously-unused gameplay scene).
- **Gate blind spot.** `reproducible + reached_end + nonzero scene` cannot detect
  *trajectory drift* within the correct level. The bad LEVEL07 passed the gate.
  The distinct-scene sanity check caught it here; a stronger gate would compare a
  late-frame RAM signature against a known-good reference (see the A/B method in
  [[EXP_2026-07-08_coverageToFrame_cycle_neutrality]]).
- Coverage stays in the correct level and is reproducible, so the executed
  function SET per level is robust even where a run's exact path differs.

## Evidence / links
- Substrate + census: [[SYS_decomp_substrate]] · [[SYS_function_census]].
- Cycle-neutral coverage RPC that made the sweep possible:
  [[EXP_2026-07-08_coverageToFrame_cycle_neutrality]].
- Campaign context: [[EXP_2026-07-08_c_decompilation_campaign_v2]].
