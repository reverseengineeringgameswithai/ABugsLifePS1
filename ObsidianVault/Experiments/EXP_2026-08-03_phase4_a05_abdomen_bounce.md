---
kind: experiment
id: EXP_2026-08-03_phase4_a05_abdomen_bounce
name: Phase 4 A05 abdomen-bounce bounded exhaustion
status: confirmed_bounded
created: 2026-08-03
updated: 2026-08-03
confidence: confirmed
source_state: pristine_static_and_validated_retained_capsule
systems:
  - SYS_abdomen_bounce
artifacts:
  - analysis/phase4_a05_abdomen_bounce.json
  - src_re/abdomen_bounce_80048138_8004abf4.c
  - tools/phase4_a05_static.c
---

# Phase 4 A05 abdomen-bounce bounded exhaustion

## Decision

A05 remains `partial` under the strict all-context Phase-4 definition, but its
high-yield row-specific work is exhausted. Move on. No new Interpreter movie,
live DuckStation run, or cold boot is required for the covered questions.

The named residuals are broad non-Training actor/terrain execution, exceptional
pause/save/death interruption, pointer-alias-complete writer proof, and exact
campaign-wide presentation timing. Those have low marginal return unless a MOD
dependency promotes one.

## Capsule-first preflight

The relevant retained evidence was the D10 Bonus-1 capsule, not an A05-named
capsule:

`~/Downloads/ABL-external-evidence/trace-capsules/Phase4/bonus-objectives-v2-20260719/Bonus_Level_01`

Manifest SHA-256:
`8e83d3171119f6786052e246b1f2b7d4033d61ad02a537ec56bb8afc08e35413`.
The manifest/capture report complete, not truncated, with no error and a clean
control fingerprint. The source movie is CachedInterpreter, so it remained
offline/poll-only and was not replayed with CPU instrumentation.

The existing compiled D10 reader reconstructed 3,654 frame records, checked
10,962 RAM/VRAM/SPU hashes with zero mismatches, and counted 145,850,969 passive
flow instructions. Its output SHA-256 is
`cab1c5fa93598705e2dcc956d95ef463fda0e8e489f3f85ad7746fbc9d3a1a8b`.

## C static-ASM investigation

A transient C disassembler/scanner read the pristine executable directly:

- executable: `REBUILD/files/SCUS_942.88`
- SHA-256: `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`
- final reducer source: `4143e85f34f2d123f5bba51567884e4f6f77c66bdd398caa99892973f95de3e4`
- compiled reducer: `ba292e2d1cffebef008e7ce88617ae50c23542b135073ec0b48ac9c63a4f4107`
- output: `35f0270d3ca822d28247610ac3641764fc5356a68730cf08b3c82e5214ce0348`

The result corrects the stale trigger wording. The Phase-2 `<=20` frame
double-tap recognizer is not a native timer. In `FUNC_80048138`, the second
Cross-active airborne action reaches state-2 handling. A floor gap below 8193
selects state 3. A gap at or above 8193 writes phase 10, state 4, event 27, and
animation selector 2 or 7.

Phase values above 1 decrement and force vertical speed to zero. Phase 1 writes
vertical speed `+4096` and stays latched. State 4 plus grounded enters the impact
block, which writes phase `-6144`, action timer 12, vertical speed zero, and
state 1. Negative phase then advances by `+512` per gameplay update.

## C capsule reconstruction

A second transient C reader independently reconstructed the capsule domains and
printed player and live-spider fields around all five accepted contacts. It
again checked 10,962 hashes with zero mismatches.

- source: `3db3d916eadf8d63f018d91d0ac226c70f9db71efc1e5770e054a46e15504b8d`
- compiled reader: `ffef9beabea968287cd3a6c1f79ba95f9c9664e118795c55372796668ce8a9b2`
- output: `c2e632ceb13129fe51fb7ffa4f0b877ad5e3d5419a4cfe74c3a2d2f0dfd0a527`

Every counter event occurred with player state 4, phase 1, and `vy=+4096`:

| Movie frame | Streak after |
|---:|---:|
| 128 | 1 |
| 352 | 2 |
| 590 | 3 |
| 742 | 4 |
| 1072 | 0, success |

The struck spider's immediate contact record always showed actor `+0x6C=-20`
and `+0x54/+0x58=4096`. Subsequent retained frames advanced `+0x6C` to `-19`
and `-18`; HP `+0x6E` did not change in those immediate windows.

## Contact-path correction and damage result

The inherited D10 note described `0x8004B31C` as an interaction-record `+0x0A`
read. Register tracing through the static body corrects that label: `s6` was set
to `player+0x7A`, so the read is player phase `+0x84`.

After the generic sphere and model-ellipsoid checks, the abdomen slice accepts
unsigned phase below 2. It rejects actor flags `0x20`, `0x40`, `0x80`, and
`0x800`, applies event `-4`, writes reaction timer `-20`, writes two `4096`
reaction fields, and calls `0x80057F44`. The function index identifies that
callee as the alternate entry to `spawn_drop_burst_8`, not a damage dispatcher.

Phase 0 then writes player `vy=-1536`, state 5, grounded zero, and animation
selector 3. Phase 1 instead reaches the challenge counter. Neither path writes
actor HP. The correct A05 wording is therefore target reaction/drop plus
qualification, not per-hit HP damage.

## Miss and reset rule

There is no miss reset and no uniqueness list. The movie retains streak four
until the fifth accepted contact. The existing compiled writer census found the
success clear at `0x8004B3D0` and shared transition/reset clears at
`0x8004A6C4` and `0x8004A854`, with no alternate direct increment or miss clear.
This remains a direct-writer result, not a proof that no pointer alias can exist.

## Why no live replay or new movie

The capsule supplies the required natural behavior, frame-boundary player and
actor state, complete domain validation, and passive block flow. The pristine
executable supplies exact admission, physics, contact, reaction, and counter
instructions. No named missing domain remained that required per-instruction
live attribution. Replaying the CachedInterpreter movie with `execTrace` would
violate the established instrumentation boundary rather than strengthen the
claim.

Request a normal-speed Interpreter movie only if future work promotes a
non-Training actor, alternate contact, or pause/death interruption question.
