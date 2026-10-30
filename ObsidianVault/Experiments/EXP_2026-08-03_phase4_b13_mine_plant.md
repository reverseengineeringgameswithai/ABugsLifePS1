---
kind: experiment
id: EXP_2026-08-03_phase4_b13_mine_plant
name: Phase 4 B13 Mine Plant bounded investigation
status: substantiated_partial
created: 2026-08-03
updated: 2026-08-03
confidence: confirmed_static_with_interpreter_behavioral_control
source_state: original_game
artifacts:
  - analysis/phase4_b13_mine_plant.json
  - tools/phase4_b13_static.c
  - ObsidianVault/Canon/Systems/SYS_mine_plant.md
---

# Phase 4 B13 Mine Plant bounded investigation

## Disposition

B13 is **substantiated partial and bounded-exhausted for Phase 4**. The pristine
resident ASM closes selection, planted arming, enemy proximity, blast construction,
damage, permanence, and quota flow. The remaining exact carried/thrown activation
writer is low-return enumeration and does not block moving on.

No new Interpreter movie is required. If the residual is later promoted, first reuse
`movies/Phase4/Interpreter/D02.movie.json`; it is already an accepted version-4,
Interpreter-recorded, normal-speed control in which the operator throws the gold mine
at input 304 and it shortly collides with a spider.

## Capsule-first audit

The retained capsule at
`~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v2/B13_mine_enemy`
passes its integrity checks:

- manifest SHA-256: `402978c7019f831dd746a9304d83480194a70995549cf9a1bc5751155c8fd621`
- `complete=true`, `truncated=false`, empty error
- 480 reconstructed records and 1,440 RAM/VRAM/SPU hash checks with zero mismatch
- clean control mismatches `{}`; final frame, cycle, RAM, registers, VRAM, SPU, and full-state fingerprints match

It is nevertheless **behavior-invalid as positive B13 evidence**. Stable plant type is
the halfword at `slot+0x00`; it never becomes 11. Quota stays `15`, and the retained
block histograms contain none of `0x8005C918`, `0x800591F0`, `0x80059210`, or
`0x80059300`. This capsule is retained only as a negative control proving that the
offline reducer does not invent a mine event.

### Decoder correction ledger

The original C pass used the correct stable type field at `+0x00`. An attempted
correction to `+0x06` was rejected after the plant record source map established that
`+0x06` is a changing animation selector.

| Pass | Source SHA-256 | Output SHA-256 | Disposition |
|---|---|---|---|
| original `+0x00` | `82b13980fc7b346fb42e6c0adca5b483351c50876fe0043e534f4a625714cfd8` | `5a7cc43c15277699eb0cc769594d01ad7563819532892080f0592ce27133f0b0` | accepted |
| attempted `+0x06` | `dc8e290610b3f47c7905859fcf20ef44d70ea2848b4ff238da8b8a39d64ad559` | `41d2fe680d3c2bd9348157255079f7a31d89cc533e10061a5ec84d1d37391091` | rejected; animation labels unused |

## C against pristine ASM

`tools/phase4_b13_static.c` reads the PS-X EXE directly, maps virtual addresses from
the executable header, extracts the relevant tables, locates the collision-pointer
alias, and fails if any pinned instruction word changes.

```bash
cc -O2 -std=c11 -Wall -Wextra -Werror tools/phase4_b13_static.c -o /tmp/phase4_b13_static
/tmp/phase4_b13_static REBUILD/files/SCUS_942.88
```

- source SHA-256: `412c2931fb6103946308979ecd6b3c9ea5b8126cd43d3c2d8743d8c14e473970`
- binary SHA-256: `ef2781b132b1c28407181eb7100eb665454836efec1e0f38dd5f305ead0e9dc4`
- output SHA-256: `5e7a42f8e2314f660e47708b4429b2e9a61816bb4d05843878d27378c1c5bb1`

## Selection and planted arming

Yellow output table indices 18 and 19, tiers 3 and 4, are both `{type=11,
extra=0}`. Plant walker dispatch index `11-2=9` is `0x8005C918`.

The common plant walker calls the handler only for a mature slot. In the mine
handler, `slot+0x02 == 1` is the planted armed state. It walks the null-terminated
enemy pointer table at `0x80090748`, skips candidates whose `enemy+0x5C` has either
bit in mask `0x00A0`, and calls the byte-matched three-axis helper `0x80052508` with
radius `150`.

The exact law is strict and quantized:

```c
((dx >> 8) * (dx >> 8) +
 (dy >> 8) * (dy >> 8) +
 (dz >> 8) * (dz >> 8)) < 150 * 150
```

Flik is not in this candidate list, so Flik proximity alone cannot detonate a
planted mine. A qualifying enemy switches the slot through the explosion animation
script at `0x8005C8D4`. Terminal resolution requires `slot+0x02 == 2` and
`slot+0x04 == 0x00060000`.

## Blast record and target set

At the terminal gate, `0x8005C9B0` calls `contact_alloc` with constructor 56 and
mode 3 at the mine coordinates. Constructor metadata row 56 is:

`0000010064000001d007d00700000006e47f0000`

The contact collision handler explicitly establishes `s5 = 0x800B0D18` and
`s1 = s5 + 8` at `0x80058BEC`. That eight-byte alias is why the constructor fields
appear at the historical hit-pointer offsets:

| Handler-relative field | Contact-record field | Value |
|---|---|---:|
| `s1+0x20` | record `+0x28` | 2000 |
| `s1+0x22` | record `+0x2A` | 2000 |
| `s1+0x24` | record `+0x2C` | 0 |
| `s1+0x27` | record `+0x2F` | 6 |

The blast therefore enters ordinary enemy damage with class 0, which subtracts 2
from the actor-local `+0x6E` hit counter. It is **not an unconditional instant-kill
override**. If the actor survives the `-2`, no permanent death tail runs yet.

The effect helper `0x800583F4` also emits 24 alternating constructor-12/13 debris
records, performs positional SFX gating, and plays sound 13. This investigation does
not promote those 24 effect records as 24 independent damage hits.

## Permanent death and quota

When the mine hit is lethal, `contact_vs_actor_handler` observes `s1+0x27 == 6` at
`0x80059200..0x80059210` and sets the permanent bit `s7 |= 2`. The common death tail
then:

- writes enemy `+0x6E = 999`
- clears `+0x60`
- sets state bits `0x0880` and clears active bit `0x0002` at `+0x5C`
- replaces `+0x70` with the hit/death program
- decrements `0x800A658E` once at `0x80059300`
- calls `0x8005182C(0x80090B68)` if the decremented quota is zero

This closes the old construction-site residual: constructor 56 itself supplies the
`0/6` permanence tuple through metadata row 56 and the `record+8` collision alias.

## Player and carried/thrown boundary

The player cannot trigger the planted enemy-proximity scan. At terminal blast
resolution, a separate `slot+0x2E & 0x40` branch can call the shared player-damage
handler at `0x8005C9F8`; the mine handler then clears bits `0x40` and `0x02`.
Thus trigger safety and blast safety are distinct.

The synchronized D02 movie is sufficient behavioral evidence that the carried mine
can be thrown and collide with an enemy. Its previous clean and armed normal-speed
runs ended at identical emulator frame `267319`, cycle `151356445709`, and RAM SHA-256
`de03646f236492b97ce7ddd38e99a9453608103f0fa373517a7a14e7b7e35ef4`, with an
untruncated trace. That watch set targeted actor `+0x20`, not the mine state machine,
so it does not identify the exact carried/thrown transition writer.

## Closure boundary

Closed for B13:

- yellow tier selection and type dispatch
- planted armed state and enemy-only trigger
- exact three-axis trigger radius and candidate exclusion
- terminal blast constructor and field set
- ordinary `-2` damage and non-instant-kill boundary
- mine permanence bit, death tail, and quota decrement
- Flik-proximity negative and terminal player-damage branch

Low-return residuals:

- exact carried/thrown-to-terminal transition writer
- one modern Interpreter trace containing ctor-56 allocation and quota decrement in the same run
- species-by-species survival breadth for local HP greater than 2

Move on. Reopen only for a MOD that needs the thrown transition owner or for full
runtime promotion. Reuse D02 before requesting any new recording.

## Durable links

- [[SYS_mine_plant]]
- [[SYS_seed_plant_behaviors]]
- [[SYS_enemy_death_and_permanence]]
- [[FUNC_800583F4]]
- [[FUNC_80059E44_spawn_drop]]

