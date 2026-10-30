---
date: 2026-08-04
phase: 4
row: C07_blue_berry
status: substantiated-partial-bounded-exhausted
tags: [phase4, blue-berry, super-berry, projectile, damage, static-analysis]
---

# Phase 4 C07: Blue/Super Berry

## Scope and evidence choice

Resolve what makes blue stronger than red, whether berry-tough actors admit it, and whether its arc, visibility flags, audio, defeat, or retirement differs. A08 already owns common throwing/trajectory and D04 owns the five-berry resistance law, so this pass tests the exact blue row and reuses those accepted domains rather than replaying them.

No C07 capsule matched the retained registry. No live escalation was justified: resident ASM answers the parameter and branch questions, while existing runtime evidence contains both required class controls.

Pristine input: `SCUS_942.88`, SHA-256 `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`.

Runtime donors:

- `analysis/phase4_d09_redbug_identity.json`, SHA-256 `1a45d3bf839f17fdf4b371571669fbdb6575540f2d1a393e45d56155b49cef4b`: ordinary Redbug HP `6 -> 4 -> 2` from blue throws.
- `analysis/phase4_d13_shell_bug_armor.json`, SHA-256 `51ad51bb93c9843e88511fd52fc846e58dd4191e1a0734842db203333c81ce3c`: bit-`0x40` shell bug HP `3 -> 1`, reproduced in separate blue trials.
- `analysis/phase4_d04_evidence.json`, SHA-256 `d09458149edcf67482cbdb545e0818eb15e1d12bbbbc66a5b4a485a09247d3f6`: accepted ordinary/tough class synthesis.
- `analysis/phase4_a08_bounded_exhaustion.json`, SHA-256 `3535a9762ff2cca4bd9706960034c4ed71aec8aeccec9a0804201092d2536be9`: accepted straight trajectory, ownership, and retirement.

Available state anchors are `blueberry.sav` (`94146512a60e4f2e4ed88fe635d706360747d1aa390a596b97ccc2cc2c326286`) and `blue_berry_walk_up_to_collect.sav` (`c219ecc6f03b6bb07966f9b33ac7f9fa2b03913e6f6a797c2b8c6d94f72f43da`). Neither was needed for a duplicate live replay.

## C-based pristine ASM result

The durable gate is `tools/phase4_c07_static.c`:

```bash
cc -O2 -Wall -Wextra -o /tmp/phase4_c07_static tools/phase4_c07_static.c -lcrypto
/tmp/phase4_c07_static SCUS_942.88
```

The exploratory C pass produced SHA-256 `2e98aa65657cedac5923307690d124b74635d9dda0fd80ab41e3c038f9300431` and passed every semantic anchor later retained by the durable gate.

Selector 1 maps to constructor type 5 at `0x800471A8..0x800471B0`. Its table row is `0x80079480`. The stored record class is 2, timer 100, model/marker 110, connection class 2, flags `0xE5`, damage byte 0, and trailing presentation bytes `[0x20,0x80]`.

## Exact comparison with red

Only four of the 20 parameter bytes differ:

- Row `+0x0C`: connection class `1 -> 2`.
- Row `+0x11`: damage byte `0x70 -> 0x00`.
- Row `+0x12/+0x13`: presentation tuple `[0x12,0x00] -> [0x20,0x80]`.

Timer, model/marker, physical fields, scale/orientation fields, and flags are identical. Blue therefore uses the same straight ballistic path, active/render flags, ownership limit, and terminal cleanup as red. The changed trailing bytes prove a presentation distinction exists, but do not by themselves name its GPU or palette owner.

## Damage and resistance

The contact scan uses `s1 = allocation base + 8`. Its `s1+0x24` class read therefore sees blue class 2, and `s1+0x2C` sees blue damage byte 0.

For a berry-tough actor, both reaction-only comparisons require value 1. Blue supplies 2 and 0, so both comparisons fail and control reaches common damage. Damage byte 0 selects the explicit `-2` arm at `0x800590C4`; `0x800590E4` stores the result to enemy-local counter `+0x6E`. Ordinary actors enter the same arm directly. The Redbug and shell-bug controls confirm `-2` on both runtime classes.

Blue class 2 is not permanent class 11, and its secondary marker 1 is not 6. Counter exhaustion therefore installs the shared temporary hit/death program without decrementing `0x800A658E`.

Blue damage byte 0 is also the class admitted by the grasshopper bonus-3 streak gate at `0x8005916C`. The challenge counter and reward remain F18/D06 behavior rather than C07-owned lifecycle.

## Collection, audio, and retirement

The collectible dispatch writes selector 1 at `0x800542C8` and uses pickup sound `0x35`. Accepted construction uses common throw sound 2. A08 closes retirement on timer zero, floor intersection, far-distance cull, missing active/render flags, or terminal hit cleanup, with the four-shot ownership counter balanced.

Exact SPU ownership of impact feedback and exact GPU meaning of `[0x20,0x80]` remain presentation residuals; neither changes blue's mechanic.

## Closure decision

**Substantiated partial, bounded-exhausted.** Damage, resistance, trajectory equivalence, visibility flags, collection, known sounds, defeat type, and retirement are closed. Strict Full remains partial only for presentation/GPU/SPU ownership, boss-overlay exceptions, and redundant campaign-wide visual breadth.

No Interpreter movie is required. Reopen only for contradictory named-family behavior or an explicit presentation/audio deliverable.

Structured evidence: `analysis/phase4_c07_blue_berry.json`.

