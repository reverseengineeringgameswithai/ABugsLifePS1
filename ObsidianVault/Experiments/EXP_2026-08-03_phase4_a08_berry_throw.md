---
title: Phase 4 A08 berry throw bounded exhaustion
date: 2026-08-03
status: bounded_exhausted
source_state: original_game
row: A08_berry_throw
---

# Phase 4 A08 berry throw bounded exhaustion

## Question

Can A08's original aim/arc law, five native berry cases, contact-object ownership, admission, and retirement lifecycle be closed from pristine code and retained evidence, or is another Interpreter movie required?

## Method

- Queried the retained Phase 4 capsule manifest first. It contains no A08 or berry-projectile capsule.
- Verified the pristine executable and staged rebuild input both have SHA-256 `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`.
- Ran `python3 tools/build_identity.py --verify`: `PASS: 327/327 staged inputs match their pins`. Python was used only for the repository identity helper, not analysis.
- Compiled and ran the C analyzer `tools/phase4_a08_static.c` against the pristine executable and retained ASM. Analyzer SHA-256: `c4982a19a4006c2b85da95d336573e5ccded7e90ee81ca1d2893c72069fd52ba`.
- Raw C result: `analysis/phase4_a08_static.json`, SHA-256 `f3f4c8bb4cbf4fb8a5b6898ad767d8838f14ad4230e7a081dd8583f59b4759d1`; every ASM/raw-opcode gate passed.
- Cross-checked the static straight recurrence against `analysis/phase2_pool_arc_oracle.json`, SHA-256 `af66f44d1ad6ed5c60ebe7d008597b9366cb9e36a67f60f8f1b11fead6fa1ce1`.
- No DuckStation session, memory mutation, disc mutation, or save/movie mutation was used.

## Observation

### Admission

The player update recognizes a new active-low Square edge through mask `0x8000`. It denies admission when action state `+0x86 >= 7`, owned throw count `+0x96 >= 4`, `+0xA3 != 0`, carried-object gate `0x800A657A != 0`, mode `+0x88` is `8`, `10`, `13`, or `17`, latch `+0x9E >= 12`, or `+0x84 != 0`.

Admission writes action state `18`. The constructor does not run immediately: the sole call to `0x800470AC` occurs when the subsequent action/animation state reaches `10`.

### Dispatch and parameter rows

| Equip index | Berry | Primary type | Timer | Model | Sub-index | Flags |
|---:|---|---:|---:|---:|---:|---:|
| 0 | red | 2 | 100 | 110 | 1 | `0xE5` |
| 1 | blue | 5 | 100 | 110 | 2 | `0xE5` |
| 2 | homing | 8 | 8 | 123 | 5 | `0xE5` |
| 3 | gold | 11 | 100 | 110 | 4 | `0xE5` |
| 4 | mega | 45 | 8 | 124 | 9 | `0xE5` |

Homing child `16` and mega child `48` have timer `100` and flags `0xED`; they are the native rows with homing bit `0x08` set.

### Spawn and ballistic aim

The constructor spawns at player Y minus `12,800`, with heading-relative X/Z offsets. Shared initial velocity is:

```text
vx = 3 * (sin(heading) >> 4)
vz = 3 * (sin(heading + 1024) >> 4)
gravity = 128
```

Red, blue, and gold call `0x80046D24`. That routine filters enemies to state mask `0x1` set and `0xA0` clear, restricts them to the heading cone, and selects the nearest squared XZ distance. It predicts motion with horizon `min(floor(sqrt(distance_squared) / 96), 30)` and solves a vertical launch velocity clamped to `[-3072, 1536]`, with the capped-distance lower bound `-2560`. With no eligible target it preserves Flik's heading and uses `vy=-2048`.

The correction from a preliminary `/48` transcription to `/96` is deliberate: the code uses signed high multiplication by `0x2AAAAAAB` and then shifts right four more bits.

### Motion and homing

Straight records perform `x += vx; y += vy; z += vz; vy += gravity`. The retained red oracle independently gives active-update X/Z deltas `2982/732` and Y-delta changes of exactly `128`; duplicate adjacent samples are the capture cadence.

Homing and mega primaries use fixed `vy=-2048`. At their short timer they acquire the nearest valid XZ target and create child type `16` or `48`. The child turns by one signed quarter of angular error modulo `4096`, clamps vertical seek adjustment to `[-1024, 1024]`, and rebuilds X/Z velocity from the sine table at `>>3` scale.

### Ownership and retirement

Every accepted constructor increments `0x800A6596`, and admission limits that owned count to less than four. Straight subtypes `1`, `2`, and `4` decrement it directly during cleanup. Homing primary subtype `5` transfers to child `16` or fallback subtype `3`; mega primary subtype `9` transfers to child `48` or fallback subtype `8`. Terminal subtypes `3` and `8` decrement, so the transfer cannot leak the count.

The updater retires a record through timer expiry, floor intersection, far-distance culling, missing active/render flags, or a homing target becoming hit/invalid. Cleanup advances timer state `0 -> -1 -> 0` and dispatches subtype effects through `0x8005953C`. Accepted construction calls sound dispatch `0x8005044C` with sound id `2`.

## Inference

The five equipped berries collapse into two motion families. Red, blue, and gold share the same constructor, aim solver, timer, flags, and recurrence. Homing and mega share the same seek updater; their primary/child models and subtype effects differ, not the seek law.

## Causal confirmation

Raw executable anchors confirm the equip read at `0x80047170`, aim call at `0x80047160`, spawn call at `0x8004724C`, and the sole state-10 constructor call at `0x80049094`. The executable jump tables bind each equip and cleanup subtype to the decoded ASM blocks, including every counter decrement or homing transfer.

## Disposition

A08 remains a strict all-context `partial`, but its high-yield Phase 4 scope is **bounded-exhausted** and the direct behavior gate is **PASS**. Five new per-berry trajectory movies would duplicate two shared code families and are not required to move on.

Deferred low-return breadth is an exhaustive enemy/terrain/stage matrix, exact target-death retarget timing beyond the decoded expiry path, exact SPU attribution, and every visual-effect variant. Request a new Interpreter movie only if one of those becomes a concrete dependency. Cold boot is not required because no disc, code, or asset changed.

Machine-readable closure: `analysis/phase4_a08_bounded_exhaustion.json`.
