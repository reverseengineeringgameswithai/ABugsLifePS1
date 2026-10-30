---
title: "Phase 4 A14: plant/crack seed"
date: 2026-08-03
tags: [phase4, reverse-engineering, seeds, plants]
status: complete
---

# Phase 4 A14: plant/crack seed

## Conclusion

A14 is **Full and bounded exhausted**. Cross initiates the jump, but Cross alone
does not crack a seed. The actor/player contact envelope and seed/player state
gates arm a ten-gameplay-tick countdown. Each countdown tick decrements
`seed+0x6C` and raises seed Y by `0x800`; at zero, `0x8004D4E0` calls
`plant_spawn` (`0x8005BDBC`). The spawner resolves the selected output, fills
the cursor slot, retains a backlink to the same seed actor, advances the cursor,
and begins the plant animation sequence.

No Interpreter movie is required. A validated unused brown-seed capsule closes
the runtime lifecycle, and a C extractor/disassembler independently recovered
the exact pristine executable from the retail BIN and passed all static
contracts. The CachedInterpreter capsule was never instrumented.

## Correction to the old binding

The previous baseline said `0x8004AF80` writes `0x10000` to `seed+0x6C`. That
is incorrect:

- `0x8004AF78` loads literal `10`;
- `0x8004AF7C` stores halfword `10` to `seed+0x6C`;
- `0x8004AF80` is the following `lw v0,8(s1)` seed-Y load.

## Evidence and provenance

| Item | Identity |
|---|---|
| Retail BIN | SHA-256 `2aeafad70d12b1bd0dc63bbb106f22ced4fae070cea8eef9de4f11072e944566` |
| C-extracted `SCUS_942.88;1` | LBA 23, 471,040 bytes, SHA-256 `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20` |
| Brown movie | SHA-256 `a32c768a9f98b5ad2ce543c0053f07e917be8efb10778ea36e1531bcdf508bd9` |
| Start state | SHA-256 `93b2b9de4de058c37eb637f3db2b2a7a0d06548117f02b87ec49d5f8c3158b84` |
| Capsule manifest | SHA-256 `902bfdfffa3dcb6ef11d7ab77405ad306a96a330bb344e85944a46a20f88b1dd` |

The C manifest checker found complete source/output, empty errors,
`truncated=false`, forced CachedInterpreter recorded explicitly, empty
mismatches, cycle neutrality, and offline reconstructability. The reducer
verified 7,146 embedded domain hashes across RAM, VRAM, and SPU state.

Machine-readable evidence is in `analysis/phase4_a14_plant_crack.json`.

## Trigger admission

The shared gates in `0x8004AE94..0x8004AF04` require:

- seed flags `+0x5C` include `0x20` and exclude `0x40`;
- existing crack timer `+0x6C` equals zero;
- seed field `+0x5E` is nonzero;
- the preceding 3D contact envelope passes.

Two static arms reach the same countdown:

1. `0x8004AEE4`: player air state `+0x84 == 1`, the established
   Cross-held jump phase. This arm bypasses the later normal-landing tests but
   retains the shared contact/seed gates.
2. `0x8004AF7C`: the normal path additionally requires player Y above seed Y,
   player `+0x9F == 0`, nonnegative vertical velocity (descending/stationary),
   action `+0x7C != 0`, and air state `+0x84 != 17`.

The accepted effect writes countdown `10`, player vertical velocity `-0x600`,
air state `3`, action `5`, clears two adjacent action halfwords, and dispatches
event `-15` at the seed position.

The retained movie uses the normal arm: basic block `0x8004AF74` executes
exactly four times. The Cross-held arm and another unrelated timer arm execute
zero times in this fixture.

## Countdown, lift, spawn, and growth

All four cycles obey the same law:

| Cross | Timer 10 | Spawn | Slot | Type | Cursor |
|---:|---:|---:|---:|---:|---:|
| 83 | 124 | 144 | 10 | 5 | 10 -> 11 |
| 670 | 698 | 718 | 11 | 3 | 11 -> 12 |
| 1412 | 1450 | 1470 | 12 | 8 | 12 -> 13 |
| 1927 | 1962 | 1982 | 13 | 2 | 13 -> 14 |

The countdown body executes 40 times: ten updates per plant. Updates occur
every two video frames in this fixture, subtract one, and add `2048` to seed Y,
for a total lift of `20480`. The spawn call and spawner entry each execute four
times. The linked actor is always `0x800A0854`; the live type-11 seed population
remains exactly nine, proving transformation/reuse rather than seed allocation.

Every new slot starts with animation gate `0` and extra state `0x0005`. Across
all four output types, extra state becomes `0x0007` after 28 video frames and
the animation gate publishes state `1` after 66. Later gate timing is
type-specific and belongs to each mature plant handler, not the shared A14
crack/spawn transition.

## Output selection and allocation

When source override `+0x0F` is zero:

```text
type_index = 4 * source_color + selected_output - 1
```

When override is nonzero:

```text
type_index = 4 * (override & 0x0F) + (override >> 4)
```

`0x8005BE90` stores the type selected through table `0x8007A448`,
`0x8005BF18` stores the seed backlink, and `0x8005BF3C` initializes extra
state. After allocation, the cursor wraps at 20 and skips occupied slots until
it reaches a free entry.

## Negative and malformed bounds

- Nine of thirteen Cross edges produce no plant, disproving direct Cross
  causation and supplying natural input negatives.
- Any failed shared/contact or normal-arm predicate rejects that arm.
- A nonzero crack timer prevents re-arming.
- Scene `0x11` has a specific exception for seed actor `0x8009FE04`: the
  spawner clears `0x8009FE66` and returns without allocating a plant slot.
- Selected/override indices have no bounds guard before the type table.
- The cursor algorithm assumes at least one free slot. If all 20 slots are
  occupied, its post-allocation scan has no exit and loops forever. Retail
  maintains the cursor-on-free-slot invariant, so this is a malformed-state
  bound, not an observed campaign failure.

## C artifacts

- Capsule reducer source: `/tmp/phase4_a14_capsule.c`, SHA-256
  `1b8c76473c1a85b0aa10fb54c523e108775efbbf06807cfc3b4c17171f4414fe`.
- Full event output: SHA-256
  `6e29342475d3b81998a05631f442f6462f460b402e9fcbc845046306a62fd226`.
- Growth output: SHA-256
  `b6b486e97483c876f15c24290e4a75e66ece6c631692ce17d0969b7ef4c59321`.
- Retail ISO/executable static analyzer: `/tmp/phase4_a14_static.c`, SHA-256
  `f142761618c31146525dc8c8f1a7241de9d4ec07a79fd02b9f2dc6b882945e9d`.
- Static output: SHA-256
  `626eaa7f31f10e743b863958e09c8872fc970e97ec3397a275487e6c02f7dfe8`;
  15/15 contracts passed.

## Phase 4 disposition

A14 is Full and bounded exhausted. A live replay would duplicate state and
block-flow domains already closed by the accepted capsule and pristine static
contracts. Reopen only for a demonstrated retail route that bypasses both timer
arms or violates the free-slot cursor invariant without external mutation.

See [[SYS_seed_crack_plant_spawn]], [[Seed_plant_output_binding]], and
[[SYS_seed_carry_plant_lifecycle]].
