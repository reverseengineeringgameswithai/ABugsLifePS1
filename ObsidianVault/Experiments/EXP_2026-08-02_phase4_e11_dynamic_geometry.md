---
node_type: experiment
title: "EXP - Phase 4 E11 dynamic geometry ownership and late-phase runtime"
date: 2026-08-02
status: partial
result: bounded_movie_gate
phase: 4
mechanic: E11_dynamic_geometry
tags: [phase4, dynamic-geometry, bug-bar, asm, c-analysis, interpreter]
---

# E11 dynamic geometry ownership and late-phase runtime

## Result

E11 advances from `unresolved` to `partial`. The Bug Bar arena's code owner,
pass-2 object ranges, transform/rotation leaves, update cadence, and late-phase
runtime arguments are proven. Early/mid-fight behavior and visual pass-2
index-to-piece labels require one new Interpreter movie.

This is not a strict Phase 4 closure claim. It is a bounded handoff with a named
missing behavioral fixture.

## Method decision

- No retained `E11` trace capsule exists under the Phase 4 external-evidence root.
- Offline analysis was therefore performed first over the hash-verified resident
  executable and every real level overlay using C, not Python.
- Live DuckStation escalation was limited to exact instruction attribution and
  frame cadence that frame-boundary/static evidence could not establish.
- The live run used a fresh absolute config, dedicated port/token, explicit
  `CPU/ExecutionMode=Interpreter`, pristine media, the hash-pinned Bug Bar state,
  normal-speed `debugger.resume`, and polling. No movie or fast-forward was used.
- Only the PID owned by the fresh config was stopped. Other running DuckStation
  instances were not touched.

## Identity and numbering correction

Bug Bar is player-facing stage 9 but the save reports runtime scene ID `14` at
`0x80082504`. The corrected scene dispatcher selects `LEVEL04/LEVEL1.BIN`.
Treating `LEVEL08` as the Bug Bar owner was the old string-pool-order mistake.

Pinned inputs:

- `REBUILD/files/SCUS_942.88` SHA-256
  `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`.
- `REBUILD/files/LEVEL04/LEVEL1.BIN` SHA-256
  `816667f0ba7ae2b602cc39da7c0b3b4020d1a231651d5b90e6374c66c34f39e6`.
- `level_09.sav` SHA-256
  `5e915f22186273047ffcf06d717aeebc2ae02dab3b0025d79f4f31afd80ca487`.
- Retail cue SHA-1 `25adb139e50ba28c2d9c1ecab4528e9cf004b1d5`.
- Retail BIN SHA-1 `0bc1a29748d4bd608d076495d085e825574880d1`.

## C/ASM findings

The cross-overlay census is reproduced by `tools/phase4_e11_asm_static.c`.
The primary Bug Bar controller is `0x800B3C70`, size 3,764 bytes.

- `0x800B3C58 -> 0x80029508` initializes pass-2 object 9 with fixed arguments.
- `0x800B4550 -> 0x80029508` writes object 9 XYZ every controller tick.
- `0x800B487C -> 0x800292DC` rotates objects 0 through 9.
- `0x800B49E0 -> 0x80029508` writes interpolated XYZ for objects 0 through 5.
- `0x800B4AE0 -> 0x8004A700` is the proximity/contact path into the player damage
  handler, with computed direction/position arguments.
- The ten signed rotation deltas embedded at `0x800B4BEC` are
  `[-100,+120,-90,+144,-110,+128,+32,+32,+32,+64]`.
- The six interpolation limits embedded at `0x800B4C00` are
  `[92,96,112,100,104,88]`.
- The four controller target coordinates at `0x800B4C24` are
  `[207872,68864,-78848,-197376]`.

`0x80029508` is byte-matched C. It validates the pass-2 index, stamps the object
attribute, follows the nested transform pointer, and writes XYZ. `0x800292DC`
applies per-object rotation. The actor-state leaf `0x8004C10C` is also exact from
the C decoder:

- `actor+0x44 = a1`.
- `actor+0x4C = 0x80077E28[a2]`.
- `actor+0x40 = first_program_byte << 16`.

The all-overlay direct-constant scan found no direct `0x8012C1D0` materialization.
This does not prove the shared buffer is unused indirectly; it proves it is not the
direct owner exposed by the Bug Bar overlay call chain.

## Runtime findings

The state loaded paused with validated media and scene ID 14. The live enemy slot
was `0x80090748 -> 0x8009FD80`, callback `0x8004A0F4`, and mover program pointer
`0x800777A4`. The anchor had boss HP 0 and is therefore late-phase evidence.

Round 1 ran at normal speed from frame 145344 to 145646:

- 302 emulator frames.
- 61 calls to `0x800B3C70`, exactly one every five frames.
- 610 calls to `0x800292DC`, exactly ten per controller tick.
- 427 calls to `0x80029508`, exactly seven per controller tick.
- 366 of those transform calls came from the six-object path loop.
- 61 object-9 transform calls came from `0x800B4550`.
- 1,037 writes hit the four watched overlay-global regions.
- No event stream was truncated.

The one-second register round covered 12 controller ticks and captured 216 events:

- 120 rotation calls, indices 0 through 9 on every tick.
- 84 transform calls, object 9 plus objects 0 through 5 on every tick.
- At frame 145649 object 9 received XYZ `(2152,-88,0)`.
- At frame 145649 objects 0 through 5 received six distinct XYZ triples and those
  triples changed on subsequent ticks.
- The player damage handler had zero hits in this late-phase, no-input window.
- The trace was not truncated.

## Observation, inference, and limits

Observed: the exact PCs, arguments, write sites, cadence, scene ID, actor pointer,
and call counts above.

Inferred with strong static support: pass-2 indices 0 through 9 are the rotating
arena object set; indices 0 through 5 are its independently translated path subset;
index 9 is the separately steered transform.

Not yet claimed: which visible bar/barrier/platform corresponds to each index,
the early/mid-fight state schedule, contact/damage timing, reset/post-fight behavior,
or generalization to every moving platform in other scenes.

## Required movie

Record one movie under `movies/Phase4/Interpreter` with a matching state anchor:

- Use pure Interpreter mode while recording.
- Start before or at Thud HP 50, not the current HP 0 late anchor.
- Cover at least one clear rolling phase and one player/arena contact.
- Continue through the post-fight transition if practical.
- Replay at normal speed for phase-sensitive checks; do not use fast-forward.
- Cold boot is not required because no disc/code/asset was changed.

The follow-up will arm `0x800B3C70`, `0x80029508`, `0x800292DC`, and the
`0x8004A700` contact path, then correlate the call arguments with frame captures.

## Transient evidence

Evidence root: `/tmp/abl-phase4-e11-20260802`.

- `e11_static_census.c` SHA-256
  `d08b117068630cea7c712581544061bff9aa375c869785bc56aa594f4bdfc55c`.
- `e11_static_census.tsv` SHA-256
  `c5200a0bfad30a3e2a76a0f27277e0d9be81c5963b9094d83820795816a4702e`.
- `e11_static_summary.txt` SHA-256
  `3e86b7cc84be65a4b37772e5296af5cffcc96cc647dfabf83a83f094e7d4f472`.
- `e11_decode_4c10c.c` SHA-256
  `1663b3c3e19fa0cf6925ef6fe3e12bfc148127a05c5cf9b14098affd4aa95af2`.
- `e11_decode_4c10c.txt` SHA-256
  `b90b7f8ceed5358b75463109a8d3c48e96da314c0739a7350c985c963a19502f`.
- `e11_runtime_60hz_round1.txt` SHA-256
  `fc2649e95690ee418c3db971f068b79d62561bfbd5eb8654c87e159a47841d68`.
- `e11_runtime_60hz_registers.txt` SHA-256
  `e8c4d406ec619a3d86d94ee9d31ee3e800fd73c8b226b01b8cce422b345ce655`.

## Reproduction commands

```bash
cc -O2 -std=c11 -Wall -Wextra -Werror tools/phase4_e11_asm_static.c -o /tmp/phase4_e11_asm_static
/tmp/phase4_e11_asm_static
```

The live command transcript, media hashes, frame/cycle bounds, and trace summaries
are retained in the transient evidence files above.

## Related

[[SYS_thud_bug_bar_boss]] | [[FUNC_80029508]] |
[[FUNC_800292DC_object_rotation_matrix_apply]] |
[[FUNC_8004B940_mover_actor_update]]

## Deep-dive closure audit (2026-08-02)

Decision: **E11 remains substantiated partial and may be left now; it is not a strict Phase 4 solved row.**

The follow-up used a compiled C parser against all 15 retail scene DATs and a C context extractor against the remaining overlay ASM callsites. No DuckStation replay was required because the missing questions were authored capacity and static caller breadth.

### Campaign-wide authored pass2 frontier

Only four scenes have a non-empty pass2 authored-object table:

| Runtime scene | DAT | Max index | Non-null slots |
|---:|---|---:|---:|
| 3 | `LEVEL03/LEVEL.DAT` | 28 | 29 |
| 4 | `LEVEL04/LEVEL.DAT` | 5 | 6 |
| 14 | `LEVEL04/LEVEL1.DAT` | 9 | 10 |
| 15 | `LEVEL05/LEVEL1.DAT` | 1 | 2 |

All other scene DATs encode `max_index=-1`. These same four scenes are the complete set of overlays found by the prior direct-call census to invoke the shared pass2 transform/rotation helpers. That agreement supplies a useful positive/negative campaign control rather than relying on Bug Bar alone.

For scene 14, the ten non-null authored slots exactly match the controller's index range `0..9`. It also agrees with the normal-speed trace cardinality of ten rotation calls per controller tick and seven transform calls per tick: object 9 plus the six interpolated path objects. There is no authored-capacity/index mismatch in the bounded E11 mechanism.

### Remaining direct caller classifications

- Scene 3: `0x800B3BA8` initializes indices `0..19` through `0x80029030`; `0x800B444C` drives those twenty indices from per-index values; `0x800B462C` applies fixed `0x1068` arguments to data-selected indices in a bounded nine-element loop.
- Scene 4: `0x800B3EF8` and `0x800B3F0C` apply independently accumulated angles to a selected pair through `0x800292DC` while their timer remains active.
- Scene 15: `0x800B3D60` and `0x800B3DB0` rotate authored indices 0 and 1 after separate actor-time thresholds, using wrapped `-0x40` angle steps.

The static caller frontier is therefore sufficient for the partial claim. It does not establish the screen-visible identity or gameplay meaning of every object in those scenes.

### Guard and evidence

`tools/phase4_e11_pass2_guard.c` is the clean-checkout C guard for all 15 expected pass2 capacities and non-null object pointers. The earlier `tools/phase4_e11_asm_static.c` direct-materialization check was corrected to decode the `lui` immediate from the instruction's low halfword; the original transient register-propagation result was already independent of that defect.

Transient evidence root: `/tmp/abl-phase4-e11-deep-20260802`

- `e11_deep_static.c`: SHA-256 `868d0e6fa0e7ba5a83404deca964b7692fa916cd54fd7ba0eabb3f32791f6cbc`
- compiled analyzer: SHA-256 `a4cb22ad93abcd7c1c809290f51ea4662f8118a416500e131266deacb7054180`
- `e11_deep_static.txt`: SHA-256 `d8d0c5f4b33933bccbe60280b30efc867676526e7e92e1aa9ed95169e57d5bee`

Reproduction command used:

```bash
gcc -std=c11 -O2 -Wall -Wextra -Werror /tmp/abl-phase4-e11-deep-20260802/e11_deep_static.c -o /tmp/abl-phase4-e11-deep-20260802/e11_deep_static
/tmp/abl-phase4-e11-deep-20260802/e11_deep_static > /tmp/abl-phase4-e11-deep-20260802/e11_deep_static.txt
```

The offline nested-attribute samples were not promoted as evidence: on-disc nested pointers participate in loader relocation, so file-offset interpretation alone is insufficient to assign those six copied halfwords safely. The capacity and non-null pointer claims do not depend on that interpretation.

### Exact reopening trigger

An Interpreter-mode movie is required only to promote E11 beyond this partial boundary. It should cover pre-fight setup, active geometry motion, a positive player-contact/damage event plus a negative control, transition or defeat, post-fight state, and reload/reset behavior. Replay must be at normal speed with `debugger.resume` plus polling for phase-sensitive checks. Until strict E11 closure or a geometry-dependent MOD needs those facts, the marginal static work is low and moving to another row is appropriate.
