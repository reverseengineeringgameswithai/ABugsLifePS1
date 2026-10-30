---
kind: experiment
id: EXP_2026-07-08_coverageToFrame_cycle_neutrality
name: movie.coverageToFrame cycle-neutral movie replay
status: success
confidence: confirmed
source_state: evidence
validates: [SYS_function_census, SYS_re_evidence_policy]
fixtures: [from-boot-movie-LEVEL00-Training, from-boot-movie-LEVEL01]
artifacts: [/tmp/coverage_acceptance.py, docs/external-debugger-movie.md]
---

# EXP_2026-07-08_coverageToFrame_cycle_neutrality

## Question
Can `movie.coverageToFrame` collect resident-text PC coverage from from-boot
movies without changing the replay trajectory used for Phase-5 trace naming?

## Symptom
Normal-speed playback of the LEVEL00-Training and LEVEL01 from-boot movies
stayed in sync, but the old coverage path drifted while still reporting
`movie.status.reproducible:true`. A/B/B2 probing showed coverage runs were
self-consistent and byte-identical to each other, but differed from normal
playback at the same movie frame; the perturbation was deterministic and inside
the coverage path, not the memory card or movie anchor.

## Root-cause chain
- `src/duckstation-qt/debuggerrpc.cpp:10523`-`10558` arms
  `AddExecRangeCoverageWatch(...)` and advances the movie with turbo chunking.
- Before the fix, the coverage-only range watch used the same generic range
  instruction hook as full `execTrace.addRangeWatch`. That hook made
  `CPU::UpdateDebugDispatcherFlag` true; `src/core/cpu_core.cpp:2151`-`2167`
  then forced `CPUExecutionMode::Interpreter` for debugging.
- The recorded repro config uses `ExecutionMode=CachedInterpreter` and
  `RecompilerICache=false`. CachedInterpreter charges block fetch ticks without
  modeling the scratch I-cache in that mode; the forced pure interpreter
  fetched through `FetchInstruction`, which can add I-cache fill/read timing.
  Different guest cycle counts shift input sampling even though the movie
  remains anchored and reports reproducible.

## Fix
Chosen strategy: non-perturbing collection. Coverage-only range watches now use
a passive instruction observer when no full range trace is armed:
`src/core/debugger_control_service.cpp:4286`-`4294` selects
`CPU::SetPassiveInstructionHook`, and `ExecCoverageInstructionHook` records only
coverage counts. The passive hook is called from the normal interpreter /
cached-interpreter loops (`src/core/cpu_core.cpp:2594`, `2739`, `2791`) without
setting the debug-dispatcher flag, so CachedInterpreter playback keeps the same
execution mode and fetch timing as normal playback.

Full range exec tracing and breakpoints still use the existing debug-dispatcher
path. The earlier timing-parity edit to `FetchInstruction` compiles and remains
as a defensive improvement for forced-interpreter debugging, but the accepted
movie coverage fix does not rely on it.

## Acceptance
Command:
`python3 /tmp/coverage_acceptance.py LEVEL00-Training LEVEL01`

DuckStation source/binary: `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`
dirty tree, `build-release/bin/duckstation-qt`
sha256 `97310ee774d1807665887aa480c33b202303fa8e210c5015fec54dd0709130b6`.

Harness contract: launch isolated repro configs, normal-play each movie to two
deep checkpoints, pause and hash `0x800A6400..0x800A6BFF` plus
`current_scene_id`, then replay fresh from boot with `movie.coverageToFrame` to
the exact same movie indices. Run coverage twice and require both signatures to
match normal playback and each other, then advance coverage to near-end and
completion.

Results:
- LEVEL00-Training: normal `idx=5855 scene=0x11 sig=78e92df85451`,
  `idx=8289 scene=0x11 sig=a850bfe469d7`. Coverage B and B2 matched both.
  Near-end B/B2: `idx=9748/9750 scene=0x0 sig=a5691714ca8e`;
  `reached_end=True`.
- LEVEL01: normal `idx=6214 scene=0x1 sig=2b5b01bae300`,
  `idx=8798 scene=0x1 sig=d5f858a42b75`. Coverage B and B2 matched both.
  Near-end B/B2: `idx=10346/10348 scene=0x0 sig=517e91466c32`;
  `reached_end=True`.

## Links
- Supports runtime trace collection for [[SYS_function_census]].
- Applies the evidence rule in [[SYS_re_evidence_policy]]: movie-driving RPCs
  need normal-vs-instrumented RAM signature checks, not only
  `movie.status.reproducible`.
