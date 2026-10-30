---
id: EXP_2026-08-02_phase4_e09_bounded_exhaustion
date: 2026-08-02
status: complete
systems:
  - SYS_native_grain_gates
tags:
  - phase4
  - grain-gates
  - trace-capsule
  - static-analysis
---

# Phase 4 E09 grain-gate bounded exhaustion

## Verdict

`E09_grain_gates` is **bounded-exhausted partial**. The row's named baseline gaps are
closed: denial feedback/cadence, every authored gate location, and every threshold
source. Strict Phase 4 promotion is not claimed because only some Definition-of-Done
items are met and no retained LEVEL07 movie shows a successful `32 -> 0` opening.

No live DuckStation run was needed. Twelve retained E09 capsules were validated before
analysis, then queried in C. Runtime overlay RAM, rather than the stale historical
LEVEL02 listing, was the static target.

## Capsule validity and scope

- Central preservation set: `analysis/phase4_trace_capsule_set.json`.
- Capsules: 9 LEVEL02 and 3 LEVEL07, all `control_match: true`.
- Reconstructed records: 12,239.
- RAM/VRAM/SPU SHA-256 checks: 36,717; mismatches: 0.
- Passive flow: 16,481,113 blocks/count items and 473,406,509 guest instructions.
- Frame-boundary evidence only; not an every-cycle trace.
- Every movie, start state, capsule manifest/tree, and the exact DuckStation binary is
  hash-pinned by the central preservation set.

## LEVEL02 mechanism

The live overlay iterates nine records at `0x800B4C1C`, stride `0x14`, with fields
`{state, object_id, threshold, x, z}`. The exact census is in
`analysis/phase4_e09_static.json`.

At `0x800B44BC`, grain `u8 0x800A65A1` is compared with record `+8`. Sufficient means
`grain >= threshold`. The success path then tests:

```text
(((player_x - gate_x) >> 8)^2 + ((player_z - gate_z) >> 8)^2) < 10000
```

Success dispatches SFX 63 through `0x80050994`, writes `4295 -> 4200` at
`0x800B4530`, then the update path writes `state -= 140` at `0x800B4624` while the
old state is at least 1801. All five observed openings therefore have 19 transitions
and terminate at 1680. Every transition is separated by two emulator/movie frames.
Resident `0x80029030` receives `(object_id, 4200, new_state, 4200)` and applies the
object's fixed-point transform coefficients. Records 0 and 4 are paired: opening either
also writes the other's state and clears the corresponding object-slot field.

When grain is insufficient, feedback is limited to the tighter planar test `<1600`.
It calls `contact_pickup_sfx` `0x80050C40` with ID 76, then arms cooldown
`0x800B4D10` to `next_cursor_byte + 60`. The main overlay update decrements a positive
cooldown once per call. Capsules observe arms from 132 through 306 and overwhelmingly
two-frame decrement cadence; isolated longer gaps occur only across separate arms.

Observed complete openings:

| Movie | Record | ID | Threshold | First transition | Terminal transition |
|---|---:|---:|---:|---:|---:|
| gate01 | `0x800B4C58` | 22 | 10 | m804 | m840 |
| gate03 | `0x800B4C80` | 21 | 20 | m399 | m435 |
| gate05 | `0x800B4C44` | 24 | 10 | m87 | m123 |
| gate06 | `0x800B4C30` | 23 | 10 | m66 | m102 |
| gate08 | `0x800B4C94` | 28 | 30 | m622 | m658 |

The other LEVEL02 capsules are useful denial/closed controls; their target state does
not change.

## LEVEL07 mechanism

LEVEL07 uses a separate function at `0x800B3D84`. Gate state is three `s32` entries at
`0x800B4570`; closed is `-1`. Threshold is computed, not table-loaded:
`10 * (gate_index + 1)`, giving 10, 20, and 30.

`0x800524B8` proves proximity as planar squared distance `< radius^2`. The three call
sites provide all positions/radii and paired object/delta arguments; see the static JSON.
On success the overlay dispatches SFX 63, writes state 32, and each update decrements it
while translating two authored geometry channels through `0x800292DC`. The terminal is
0. Denial uses the same ID-76/cursor-byte-plus-60 cooldown design at `0x800B456C`.

The three retained LEVEL07 movies are exact one-short controls: grain 9, 19, and 29;
their target entries stay `-1`, denial cooldowns arm, and no success path executes. Thus
the success mechanism is exact static evidence but not behavioral confirmation.

## Reproducible C artifacts

- `tools/phase4_e09_capsule.c`: reconstructs and SHA-checks capsule domains, discovers
  gate transitions, measures cooldown cadence, hashes runtime code, and joins passive
  flow. Source SHA-256 before banking:
  `f4f1be2d955828967782cb8cd2c5c1468af9c6e00afedf96695aa470a1c39066`.
- `tools/phase4_e09_mips_static.c`: decodes runtime MIPS, scans grain/state/helper
  constants and direct global xrefs. Source SHA-256:
  `c3924a727c89928f7522729599bcdc5d6b251886cd2a2660ef9617a8e497c126`.
- `tools/phase4_e09_manifest_audit.c`: dependency-free extraction of the 12 E09
  preservation objects. Source SHA-256:
  `f0018dd18636c80d5801fb95a0fc4cfbc2c04983661e89db47fddac69a0adfbd`.
- `analysis/phase4_e09_capsule.json`: full C result; SHA-256
  `4e19cddbb3505b8df3429434db2a5e15f168c33e382a71db46dcef7b53bd4d8d`.
- `analysis/phase4_e09_runtime_disasm.txt`: focused runtime-overlay disassembly emitted
  by the C decoder.
- `analysis/phase4_e09_bounded_exhaustion.json`: strict nine-item scorecard.

Representative commands:

```bash
cc -std=c11 -O2 tools/phase4_e09_capsule.c -lcrypto -lzstd -o /tmp/e09_capsule
E09_DUMP_DIR=/tmp/e09-ram /tmp/e09_capsule \
  ~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v2/E09__* \
  > /tmp/e09_capsule.json
cc -std=c11 -O2 tools/phase4_e09_mips_static.c -o /tmp/e09_static
/tmp/e09_static --window /tmp/e09-ram/E09__LEVEL02_gate01_closed_open.ram.bin \
  0x800B4380 0x800B4660
```

## Stop boundary and movie request

The remaining work is not another useful ASM drill-down. Strict closure would require a
complete overlay writer/callee frontier, reset/save-load/transition lifecycle, reviewed
LEVEL07 semantic C, a durable oracle/promotion gate, and behavioral breadth.

No new movie is required to support the bounded-exhaustion verdict. To advance strict
closure, record one Interpreter-mode LEVEL07 success: gate 0 at exactly 10 grain is the
smallest case; approach from outside radius 80 and remain until state completes `32 -> 0`.

## Links

[[SYS_native_grain_gates]]
[[Phase 4 - Solve Every Gameplay and Engine Subsystem]]
