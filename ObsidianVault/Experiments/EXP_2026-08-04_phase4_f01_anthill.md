---
date: 2026-08-04
phase: 4
row: F01
subject: Anthill representative full-stage completion and results handoff
status: substantiated_partial
closure: bounded_exhausted
disposition: move_on
continued_by: EXP_2026-08-05_phase4_f01_objective_lifecycle
evidence_json: analysis/phase4_f01_anthill.json
static_tool: tools/phase4_f01_static.c
scenario: tools/scenarios/duckstation/phase4_f01_anthill_completion.yaml
---

# Phase 4 F01 - Anthill completion and results handoff

> **Continued by [[EXP_2026-08-05_phase4_f01_objective_lifecycle]] (2026-08-05).**
> That pass closed this note's `Whole objective/lifecycle` gap: the region code is a
> FIVE-ARM dispatch gated on GROUNDED, `0x800823A0` is a seven-value transition
> REQUEST rather than a completion latch, and sector 177's polygon footprint (listed
> below as a residual) is recovered. It also observed the sector index live at the
> triggering instruction, upgrading this note's sector-177 *inference* to an
> observation.

## Result

F01 is **substantiated partial and bounded-exhausted**. The synchronized Interpreter replay binds Anthill's natural ending from its authored collision-sector field through the resident player update, completion latch and timer, scene teardown, results-overlay entry, and results exit. No additional Interpreter movie is required, and the row can move on.

This is not Full closure. Exact sector polygon topology, SFX 58's sample identity, exhaustive lifecycle permutations, and compiler matching of the entire player updater remain outside the bounded high-value scope.

## Method

Phase 4's capsule gate was applied first. The retained LEVEL01 capsules cover A09/A10/A11 seed mechanics, not the natural goal trigger, timer lifecycle, teardown, or results handoff. A fresh isolated DuckStation instance was therefore justified for the named missing domain of exact instruction attribution.

The run used pristine retail media and the version-4 Interpreter movie `movies/Phase4/Interpreter/Any% Runs/LEVEL01_AntHill.movie.json`. Its movie and save hashes are recorded in the structured evidence. The user visually confirmed a normal-speed clean replay and then a normal-speed armed replay. Instrumentation was armed only after loading the movie's state anchor.

The independent C analyzer in `tools/phase4_f01_static.c` checks the pristine executable instructions, decompresses LEVEL01 `LEVEL.RAW` chunk 32 without Python, enumerates the authored sector records, and checks the MEMORY results-overlay finalizer call. Its 12 resident ASM assertions all matched, its decompressed size matched the declared 236,944 bytes, and its process returned success.

The first declarative probe exposed the known transport trap rather than a gameplay failure: the scenario launcher defaulted to CachedInterpreter, and arming `execTrace` at movie frame 1932 switched modes and desynced the goal. Pinning Interpreter removed that mode mismatch, but `movie.advanceToFrame` still did not service CPU trace watches for this phase-sensitive interval. The scenario harness now exposes `launch.execution_mode` and a `movie_frame_realtime` trigger. The final scenario frame-steps only to the clean pre-goal anchor, arms there, then uses `debugger.resume` plus `movie.status` polling for all instrumented intervals.

`tools/scenarios/duckstation/phase4_f01_anthill_completion.yaml` passed all 13 assertions. It proved the clear pre-goal state, exactly one latch store and timer store, live countdown, timer-zero teardown, one results entry, one results finalizer call, and two total entries to the shared finalizer. The isolated Interpreter process was stopped successfully by its owned config lifecycle.

## Natural trigger chain

At emulator frame `140814` (movie-relative frame `1933`, cycle `79728950068/69`), the call at `0x80049644` returned region code `2` from `FUNC_80038F38`.

`FUNC_80038F38` is byte-matched C. It returns zero unless `[Flik+0x82] == 1`; when gated, it reads the current player sector from `0x80090560 + player_index*20`, indexes the runtime sector table at `0x800A7E48` with stride `0x30`, and returns the signed region code at `+0x2E`.

The resident player update then followed the code-2 branch:

- `0x800496D8` stored `1` to completion latch `0x800823A0`.
- `0x80049704` stored `23` to timer `0x80082470`.
- `0x80049708` called the sound helper with ID `58`.

The scene-flow consumer reads the latch at `0x8004FEF0` and timer at `0x8004FF04`. The timer decremented at `0x800553F8` from 23 to 0 across frames `140814..140858`. At frame `140859`, the consumer called `transition_finalizer_subsystem_reset` at `0x80045A60`; scene state `0x80082504` changed from 1 to 0 at `0x800503AC`.

## Results handoff

The MEMORY results function `0x800B7DA0` entered once at frame `141061`, with return address `0x800B975C`. At frame `141863`, the overlay called the transition finalizer from `0x800B8750`; the observed return address `0x800B8758` is after the MIPS delay slot. Scene state traversed `0 -> 1 -> 0` during the continuation.

No execution reached the resident `level_complete_finale` at `0x8004DA94`, nor the tested `LEVEL1.BIN` completion stores/call at `0x800B4100`, `0x800B410C`, or `0x800B4164`. F01 therefore uses the resident collision-sector transition path, not the generic LEVEL1 finale path.

## Authored source owner

The C census parsed 189 sector records in decompressed chunk 32 at offset `0x36570`, stride `0x4C`. Exactly one authored sector has any nonzero region code, and it is sector `177` with code `2`. Its source origin is `(-5094, -5309, -3901)` and its runtime-scaled origin is `(-163008, -169888, -124832)`.

The live branch value is therefore tied to the unique authored Anthill exit sector rather than merely correlated with a generic completion flag.

## Causal confirmation and ruled-out confound

Existing LEVEL01 work supplied the causal mutation control: relocating code 2 from sector 177 to sector 108 on a pristine-derived rebuild caused natural traversal into sector 108 to complete the stage, while the same route on pristine media was inert. That mutation does not need to be repeated.

A previously suspected proximity actor was also ruled out. Teleporting to that actor produced death/respawn rather than level completion.

## Evidence classification

**Observation:** The synchronized armed replay captured the exact query return, branch/store PCs, RAM transitions, countdown, teardown call, results entry, and results continuation.

**Inference:** The natural route crossed authored sector 177 because the live return was code 2 and the source census proves sector 177 is LEVEL01's sole nonzero/code-2 sector.

**Causal confirmation:** Moving the authored code-2 field to sector 108 moved the completion behavior on the rebuilt disc and left pristine behavior unchanged.

## Phase 4 closure metrics

| Metric | F01 result |
|---|---|
| Campaign breadth | Partial: one synchronized natural route plus prior relocation control |
| Complete frontier | Met for the high-value trigger-to-results frontier |
| Cross-system behavior | Met: collision sector -> player update -> scene flow -> results overlay |
| Durable evidence | Met: pinned replay hashes, C verifier, passing declarative scenario, structured JSON, and this note |
| Lifecycle | Substantiated partial: natural completion/reset/results observed; exhaustive death/restart variants omitted |
| Original interfaces | Met |
| Original oracle | Met for the natural route |
| Source closure | Substantiated partial: matched query C and instruction-checked dispatch/consumer; whole updater not compiler-matched |
| Typed state | Met for sector code, latch, timer, and scene state |

## Bounded residuals

- Reconstruct the exact polygon footprint/topology of sector 177.
- Attribute SFX 58 to its exact SPU sample/cue.
- Replay every pause, death, restart, and alternate-route lifecycle combination.
- Compiler-match the complete 6004-byte player updater.
These are presentation, content-attribution, compiler, or exhaustive-breadth tasks. They have minimal return for the Phase 4 gameplay-mechanism requirement and do not weaken the bound trigger-to-results chain.

## Evidence files

- Structured record: `analysis/phase4_f01_anthill.json`
- Reusable C verifier: `tools/phase4_f01_static.c`
- Declarative regression: `tools/scenarios/duckstation/phase4_f01_anthill_completion.yaml`, SHA-256 `7a6891f84639cff5fb338147b45eca866735a1e5b6e88cfad5f6316f8833af31`.
- Passing real-time probe report: `/tmp/phase4_f01_realtime_probe_report.json`, SHA-256 `b36bf40c18ee2e38e7140db1174c4916af165b891364c36c31dbf45d4a5e55cb`.
- Exact exec trace: `/tmp/phase4_f01_exact_exec.json`, SHA-256 `a7aede3d719e90b68ec0cd1aaed9f68b1a9d89d03377ecc2d7c7ed64c8391f64`, seven events, not truncated.
- Access trace: `/tmp/phase4_f01_all_access.json`, SHA-256 `1fad52deb9f99d8ba98b98d597e4fee6802917b90fc85702b6caba8e6082a72d`, not truncated.

`/tmp/phase4_f01_exact_access.jsonl` is excluded because its query watches were configured with the wrong access mode. Earlier sparse captures and `phase4_f01_final.png` are also excluded because they preceded the user-confirmed synchronized replay.

The repeatable command is `python3 tools/run_ps1_scenario.py tools/scenarios/duckstation/phase4_f01_anthill_completion.yaml --output-dir /tmp/phase4_f01_scenario_final`.
