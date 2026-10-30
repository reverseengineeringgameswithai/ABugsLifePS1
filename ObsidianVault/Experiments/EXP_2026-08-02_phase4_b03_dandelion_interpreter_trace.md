---
type: experiment
phase: 4
row: B03
date: 2026-08-02
status: confirmed-single-fixture
method: interpreter-movie-exectrace-c-reduction
---

# Phase 4 B03 dandelion Interpreter trace

## Question

Confirm the runtime-only parts left after the C static ASM pass:

- whether latch `11` produces sustained glide;
- whether recorded steering changes `VX/VZ` during the glide;
- exact latch write/use/landing/clear timing;
- automatic release and visible canopy behavior;
- whether `execTrace` preserves the new pure-Interpreter recording.

## Evidence identity

- Retail media: `SCUS-94288`, `Disney-Pixar A Bug's Life`.
- Cue SHA-1: `25adb139e50ba28c2d9c1ecab4528e9cf004b1d5`.
- Bin SHA-1: `0bc1a29748d4bd608d076495d085e825574880d1`.
- `tools/build_identity.py --verify`: PASS, 327/327 staged inputs.
- Movie: `movies/Phase4/Interpreter/B03.movie.json`.
- Movie SHA-256: `9c0528b26d3ba25d69f834fb0b78cf853d3e01e4194c7807304ba736ec780b9a`.
- Movie format: v4, 819 frames, SCUS-94288, start-state anchored.
- Start state: `movies/Phase4/Interpreter/B03.movie.sav`.
- State SHA-256: `e4ff915614dbb01b17e6280de7405314bf24a3648e132e83d36807226da2d04a`.
- State media: the same pristine cue, serial and title; `emulator.getStateInfo` reported valid.
- DuckStation fork revision: `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5` with recorded dirty status.
- Binary SHA-256: `f34aaacd7116994885a2a5a17a9f2c517ce5ed1bfc863826fa9d9750ea5d1899`.
- Isolated config: `/tmp/abl-phase4-b03-dandelion-20260802`.
- Port: `23583`.
- Runtime execution mode: `Interpreter`, set in the isolated config before launch.
- Captured config SHA-256:
  `7ee4bc933cda89555006e5967133d13b77b5c10ccefc1f7e70404eb99ae3f3c`.

## Method

The literal user path was case-adjusted to
`movies/Phase4/Interpreter/B03.movie.json`. No cached movie was reused.

The normal `movie.traceToFrame` helper was deliberately not used because the
current implementation forces both comparison passes to `CachedInterpreter`.
That would not test the newly recorded pure-Interpreter timing contract.

Instead:

1. Replay the movie uninstrumented from its recorded state under pure
   Interpreter through frame 819.
2. Capture end frame/cycle/PC/SP and player `0x800A6500..0x800A65A7`.
3. Reload the recorded anchor.
4. Arm bounded `execTrace` ranges over dandelion, glide, normal gravity, and
   steering, plus write access logs on grounded and latch.
5. Run 600 frames, reconnect after the expected client timeout, verify the
   server completed exactly to movie frame 600, then run the remaining 219.
6. Page all 13,694 retained trace events and reduce them with C.
7. Replay without instrumentation for transient visual captures.
8. Clear traces, controller state, and movie data, then stop only PID `50837`
   through the owned launcher/config pair.

The trace command was split because `execTrace.run` accepts at most 600 frames:

```bash
duckstation_debug_client.py ... exec-trace-run --frames 600
duckstation_debug_client.py ... exec-trace-run --frames 219
```

## Determinism control

Observation:

- Control and instrumented frame: `68631`.
- Control and instrumented cycle: `38858550023`.
- Control and instrumented PC: `0x8004FEAC`.
- Control and instrumented SP: `0x801FFFD0`.
- The 168-byte player block matched byte-for-byte.
- The retained trace reported `truncated:false`. The dandelion range watch
  reached its 5,000-event bound, so writer timing is taken from the separate
  complete latch access log, not from a claim of complete handler coverage.

Conclusion:

`execTrace` was cycle-neutral for this movie within the captured end-state
boundary. This is a bounded comparison, not a full-main-RAM equality claim.

## Runtime timeline

All movie frames below are relative to the 819-frame recording:

- Frame `219`: first dandelion launch clears grounded and writes `VY=-4096`.
- Frame `239`: first `0x8005C8BC` write of latch `11`.
- Frame `241`: first player-update consumption of latch `11`.
- Frame `241`: first glide VY store is `-1792` because the sphere gate was
  reached after the ballistic launch had already advanced.
- Frame `261`: first terminal `VY=350` update.
- Frame `482`: second dandelion launch; the already-active latch produces a
  minimum observed glide VY of `-3840` on the following update.
- Frames `239..505`: 50 observed latch-11 writes while the sphere gate remains
  true.
- Frames `241..719`: 212 latch-active player updates.
- Frame `717`: native collision writes grounded `0x0101` with byte writers
  `0x80036CB8` and `0x80036CC0`.
- Frame `719`: the next player update reads grounded value `257` and
  `0x80048700` clears latch `11`.

Observation:

- 211 glide VY stores were retained.
- 183 updates wrote the terminal `350` value.
- The observed VY range was `-3840..512`. `512` is the statically predicted
  one-update overshoot before the next `350` clamp.
- Only one state `5 -> 6` store occurred, before latch activation. Latch-active
  updates bypassed the ordinary transition as predicted.

## Steering

Within the latch-active window:

- 288 movie frames contained directional input.
- 212 player-update `VX/VZ` pairs were captured.
- 165 samples had nonzero `VX` and 165 had nonzero `VZ`.
- 169 consecutive player-update samples changed the velocity pair.
- `VX` ranged from `-1906` to `1943`.
- `VZ` ranged from `-1840` to `1970`.

Conclusion:

The recording behaviorally confirms steering during sustained glide, not only
static reachability of the input code.

## Release, landing, and presentation

Instruction evidence:

- Native collision sets grounded at frame `717`.
- Grounded latch release occurs at frame `719`.
- The movie ends with player state `0`, grounded `257`, animation `22`,
  `VX=VY=VZ=0`, and latch `0`.

Visual corroboration:

- Frames `300` and `500` visibly show the overhead dandelion canopy during
  glide.
- The canopy remains visible at frames `719` and `721`.
- It is absent by frame `730` and remains absent at frame `750`.
- The visual release tail is therefore longer than the latch itself but no more
  than 11 movie frames after latch clear; exact renderer/animation ownership is
  not attributed here.

Conclusion:

Sustained glide, steering, automatic grounded release, controlled landing, and
the visible canopy are confirmed in this fixture.

## C reduction

The dependency-free reducer consumes TSV flattened from the retained debugger
JSON and performs all timing, register, velocity, steering, landing, and
control-equality calculations.

```bash
cc -O2 -std=c11 -Wall -Wextra -Werror \
  tools/phase4_b03_runtime_trace_analyzer.c \
  -o /tmp/phase4_b03_runtime_trace_analyzer
/tmp/phase4_b03_runtime_trace_analyzer \
  /tmp/phase4_b03_trace_all.tsv \
  /tmp/phase4_b03_ground.tsv \
  /tmp/phase4_b03_latch.tsv \
  /tmp/phase4_b03_movie.tsv \
  /tmp/phase4_b03_control.tsv \
  /tmp/phase4_b03_instrumented.tsv \
  > analysis/phase4_b03_dandelion_runtime.json
```

## Retained and transient evidence

Committed compact evidence:

- `analysis/phase4_b03_dandelion_runtime.json`, SHA-256
  `3c35b6b07d3ea9615ca5bea1722032ad59f8e2a5634e4476d0a5a435a1869668`.
- `tools/phase4_b03_runtime_trace_analyzer.c`, SHA-256
  `f7b7d36aac1ad561c3169f6241a0a3c299f7469f4c9b32b9ed00c5e8a6b484b3`.

Transient raw evidence under `/tmp`:

- first trace page:
  `bc4b8cb8f2d9942c4a6466826ab4aa893823105e864263844cd1744ce7fb9e56`;
- second trace page:
  `7777263056b53991cb1b677faa1c4945c9abab220ed644d0c0c45c40e9495fd2`;
- grounded access log:
  `5d2e7f047d1a1ab836440c352f9bd64cee47e6d68ba4d7f073768cabae476b79`;
- latch access log:
  `2dc083fd75a5e060f12d05368c3d063e7bc2b0d8c55ae51151c464af465a33d8`.

Screenshots remain transient and are not committed. Their hashes are recorded
in the shell transcript and can be added to a central external-evidence
preservation manifest if this fixture is promoted.

Cleanup evidence:

- stop output SHA-256:
  `52e1f41ae1c555dffa0aca47ce00184b1dfb20f49b85e5f5f33b5083d02c117b`;
- final launcher status SHA-256:
  `77b19d41a866b556f366e4e34939a741319d5c10ccefc1f7e70404eb99ae3f3c`;
- result: `not running`, no live PID file.

## Row status

B03's named runtime questions are complete for this Interpreter fixture. The C
continuation attributes the latch-gated overhead effect and player animation and
classifies direct lifecycle clears. The row remains a bounded-exhaustion
`partial`, not `solved`; only shared alias closure and deliberately deferred
low-return breadth remain. Cold boot is not required because this experiment
changed no disc, code, or asset.

## Related

- [[EXP_2026-08-02_phase4_b03_dandelion_capsule]]
- [[EXP_2026-08-02_phase4_b03_dandelion_glide_static_continuation]]
- [[EXP_2026-08-02_phase4_b03_bounded_exhaustion]]
- [[SYS_dandelion_glide]]
- `config/phase4_b03_dandelion.yaml`
