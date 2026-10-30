# Phase 4 B02 bounded exhaustion

Date: 2026-08-02

## Question

Resolve the corrected propeller sequence and exhaust the high-value ASM/runtime
questions without relying on phase-sensitive fast-forward replay.

## Evidence order

1. The retained B02 capsule was queried first. It remains valid for frame-boundary
   state and block flow, but its CachedInterpreter recording is poll-only.
2. C static analysis covered the reachable propeller handler, detach helper, and
   XZ-radius helper.
3. The corrected v4 Interpreter fixture supplied exact instruction attribution.

## Corrected playback protocol

movie.advanceToFrame results were rejected. The accepted replay used a fresh isolated
config, Interpreter selected before boot, verified pristine media, startPlayback with
load_start_state=true, and debugger.resume with status polling. Fast-forward and turbo
were disabled.

Status reported movie version 4, armed_while_paused=true, phase_delay_owed=true, and
reproducible=true. A full-handler trace captured eight registers and reached 10,000
events; the operator confirmed that the heavier flight check stayed synchronized.

## Narrow causal trace

Exact watches covered 0x8005c290, 0x8005c350, 0x8005c3d0, 0x8005c424, 0x8005c454,
0x8005c4a0, 0x8005c4dc, and 0x8005c528. A write watch covered four bytes at
0x800A655C. The replay yielded 1,662 exec events and 61 carry writes, both
non-truncated. Polling paused within 33 neutral frames after completion; every
behavior-changing event was inside the recorded input span.

Raw JSON was converted to TSV with jq and reduced by
tools/phase4_b02_runtime_trace_analyzer.c, compiled as C11 with -O2 -Wall -Wextra
-Werror.

Reducer source SHA-256:
433f11498affb4e93575e6e7111b017a20693aae38824a45f7cbba951b57caf9

Raw reduction SHA-256:
dba13076601c7abec7089a7d19324dd5f6e79d2f39745c5393f69c9f6252e935

## Results

- Inputs 86..190 contain no carry-offset write.
- Seed actor 0x800A0BF0 still receives 44 actor-lift stores during inputs 92..180.
- Input 296 executes manual throw writer 0x80047ce8, changing 3696 to 0.
- The loose seed receives 15 actor-lift stores during inputs 298..326.
- Player lift begins at input 401.
- Input 565 executes pickup writer 0x80047858, changing 0 to 3696.
- Input 779 executes detach writer 0x80046d04, changing 3696 to 0.
- Player and seed actor lift stores both occur at input 779.
- All 59 detach calls pair with the 59 player-velocity stores.
- All 10 player clamp stores write exactly -3072.
- All 94 actor-velocity stores pair with 94 same-pointer flag clears.
- Actor vertical velocity reaches -3584, consistent with no actor clamp.

## Interpretation

Ordinary carried approach does not release the seed. The first launch setup requires
throwing the seed onto the propeller. Later, after pickup at height, the player's
qualifying free-fall contact enters the player-lift path and calls the detach helper;
the same handler invocation then lifts the detached seed through its actor scan.

## Closure

B02 is bounded_exhausted_high_value. No new movie or cold boot is required. Deferred
work has minimal return: exhaustive RNG-byte distributions, every placement/non-seed
actor class, and pixel-level trajectory reconstruction.

Artifacts:

- analysis/phase4_b02_propeller_static.json
- analysis/phase4_b02_propeller_capsule.json
- analysis/phase4_b02_propeller_runtime.json
- ~/Downloads/ABL-external-evidence/phase4/B02_propeller_interpreter_exec_20260802
