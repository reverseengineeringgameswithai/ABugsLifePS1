---
date: 2026-08-04
phase: 4
row: C06_red_berry
status: substantiated-partial-bounded-exhausted
tags: [phase4, red-berry, projectile, damage, static-analysis]
---

# Phase 4 C06: red berry

## Scope

Resolve red's exact constructor fields, ordinary-enemy damage, berry-tough reaction, temporary/permanent consequence, and projectile lifecycle. Do not repeat A08's shared trajectory campaign or D04's full five-berry resistance campaign unless C06 exposes a distinct branch.

## Evidence selection

The retained Phase 4 capsule registry has no C06 or red-projectile capsule. No live escalation was needed because the missing domains are resident instruction flow and table data, while accepted A08 and D04 evidence already supplies runtime controls for the shared motion and two resistance classes.

Pristine input: `SCUS_942.88`, SHA-256 `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`, load address `0x80010000`, text size 468992. No overlay participates in this path.

Shared evidence was hash-checked before reuse:

- `analysis/phase4_a08_static.json`: `f3f4c8bb4cbf4fb8a5b6898ad767d8838f14ad4230e7a081dd8583f59b4759d1`.
- `analysis/phase4_a08_bounded_exhaustion.json`: `3535a9762ff2cca4bd9706960034c4ed71aec8aeccec9a0804201092d2536be9`.
- `analysis/phase4_d04_static.json`: `c2282dd9563de96552443d06544b5b09a0d1b4b4f8739df5829e9b27d99b63dc`.
- `analysis/phase4_d04_evidence.json`: `d09458149edcf67482cbdb545e0818eb15e1d12bbbbc66a5b4a485a09247d3f6`.
- `analysis/phase4_d04_bounded_exhaustion.json`: `6734e0b915ddaf4b91faa1cb442129c5a8a874a3cff7b5cbbdd10cb3f4fec9d0`.
- `src_re/enemy_death_permanence.c`: `602f659817da81afbf028c6c9bf4d772b2e0b40f6ba27791474b8099791b6b7f`.

The old `red_berry_enemy_test.movie.json` is version 2 and is explicitly rejected by the scenario-framework note because it enters a BIOS exception path in the current workflow. It was not used as behavioral evidence. Its SHA-256 is retained only as provenance: `94e904ecd9c53f8c7687dbf2ad0b4d88f3f00ed276e26cc4dd703365df70d8d5`.

## C-based pristine ASM analysis

The durable analyzer is `tools/phase4_c06_static.c`:

```bash
cc -O2 -Wall -Wextra -o /tmp/phase4_c06_static tools/phase4_c06_static.c -lcrypto
/tmp/phase4_c06_static SCUS_942.88
```

The exploratory C/Capstone pass decoded the constructor and contact/death ranges directly from the pristine executable. A second minimal C gate checked the semantic anchors and produced transient output SHA-256 `31f464147f27880d2c8de56824899c52d5b5a9c4756fbb3756191890b4516967`. The durable analyzer retains 22 exact opcode anchors and the red table-row assertions.

## Constructor result

Two resident pickup/contact paths write zero to selector `0x800A6597` at `0x8005428C` and `0x80058934`. Throw dispatch maps selector 0 to type 2 at `0x8004719C..0x800471A4`.

Type 2 indexes parameter table `0x8007941C` at row `0x80079444`. Relevant values are timer 100, model/marker 110, connection class 1, flags `0xE5`, and damage byte `0x70`. Constructor `0x8005A0E0` stores class 1 to record `+0x2C` at `0x8005A2AC` and byte `0x70` to record `+0x34` at `0x8005A270`.

## Critical pointer-bias correction

The collision loop's `s1` is **record allocation base + 8**. Therefore:

- ASM `s1+0x24` is allocation-base `+0x2C`, the red connection class 1.
- ASM `s1+0x2C` is allocation-base `+0x34`, the red damage byte `0x70`.

Treating both offsets as relative to the allocation base made earlier summaries appear contradictory. With the bias restored, static ASM agrees with the observed weak red behavior.

## Collision and damage law

At `0x80058EE4`, `enemy+0x5C & 0x40` selects berry-tough handling. Red class 1 takes the reaction-only path and `0x80059054` skips damage and death processing.

When bit `0x40` is clear, `0x80058EE8` enters common damage. `0x80059074` reads red's `0x70` damage byte; it matches no special switch case, so `0x800590E0` subtracts exactly 1 from enemy-local counter `+0x6E`, stored at `0x800590E4`. This is the exact meaning of "weak": ordinary enemies require their current local-counter value in red hits, while berry-tough state produces zero damage.

If the counter remains positive, the actor stays in the hit loop. At zero or below, red sets only the temporary-hit accumulator, writes the 999 death-animation marker, clears active bit `0x2`, and installs the shared hit/death VM program. Red's connection class is 1 rather than permanent class 11, so the `s7 >= 2` block and permanent quota decrement at `0x80059300` are skipped.

The legacy 64x5 side table still decrements by 2 when its floor guard permits, but D04 proved that table is neither the kill definition nor an immunity oracle.

## Shared projectile lifecycle

A08 already instruction-binds red to the straight ballistic family: timer 100, gravity 128, shared ballistic aim/fallback, ownership limit 4, and throw sound 2. Terminal cleanup covers timer zero, floor intersection, far-distance cull, missing active/render flags, and hit cleanup, with the ownership counter balanced at retirement. Replaying those same instructions for C06 would add no new row-specific evidence.

## Closure decision

**Substantiated partial, bounded-exhausted.** C06 now has exact constructor, record layout, resistance decision, damage delta, defeat type, permanence exclusion, and lifecycle. An exhaustive movie for every named species would repeatedly exercise the same ordinary/bit-`0x40` branch and is not required for bounded Phase 4 closure.

No Interpreter movie is required now. Reopen only for a named family that contradicts the two-state law, boss-specific overlay behavior, or an explicit campaign-wide presentation matrix.

Structured evidence: `analysis/phase4_c06_red_berry.json`.

