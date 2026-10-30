---
kind: system
id: SYS_molt_boss
status: confirmed
source_state: original_game
row: D19_molt
functions:
  - 0x80049CA0
  - 0x800590E4
  - 0x800B3CC4
  - 0x800B43F8
memory:
  - 0x8009FF90
  - 0x8009FFFE
  - 0x800823A0
  - 0x80082470
evidence:
  - EXP_2026-08-03_phase4_d19_molt
src_paths:
  - src_re/molt_boss.c
---

# Molt boss

## Canonical machine contract

Molt in Battle Arena is live actor ID 29 at `0x8009FF90`, stride `0x84`. The retained full fight binds:

| Field | Meaning/value |
|---|---|
| `+0x44` | hit-acceptance gate; value 1 causes rollback |
| `+0x5C` | flags `0x5043` |
| `+0x6E` | HP, initialized to 50 |
| `+0x70` | mover-VM IP `0x80077688` (`park_seek`) at collisions |
| `+0x7C` | callback `0x8004A0A0` (sound callback) |

The earlier ID-22 and `LEVEL09/LEVEL.BIN` bindings were false hypotheses. The fight's live secondary overlay logic is byte-identical to `LEVEL03/LEVEL1.BIN`; C corpus analysis finds its HP-restore word only at offset `0x324`, runtime PC `0x800B3CC4`.

## Charge and guard

Collision-time VM IP `0x80077688` is shared mover opcode 6, `park_seek`. This is the confirmed pursuit/charge control-flow state. Exact animation naming is not established.

The resident class-0 damage writer `0x800590E4` always proposes HP minus 2. The overlay owns acceptance:

```text
previous = [0x800B45F4]
if Molt[+0x44] == 1 || [0x800823A0] != 0:
    Molt.hp = previous                  # 0x800B3CC4
else:
    previous = Molt.hp                 # 0x800B3F0C
```

The pristine movie records 43 proposed Molt stores, 15 accepted descents from 50 to 20, and 28 rollbacks. Raw dispatcher hits therefore must not be treated as effective damage.

## Crowd throw

The producer at `0x800B41CC..0x800B4468` selects one of four origins from `0x800B45B4`, aims toward Flik, gates squared X/Z distance at `0x7FFFF`, and calls `contact_alloc 0x8005A0E0` at `0x800B43F8` with contact type 71. The retained allocation trace records 31 calls with return address `0x800B4400`.

Connecting Molt contacts use class 0, `+0x24=10`, and `+0x27=1`. The old `0x800B4620/0x800B4750` candidates belong to the wrong overlay and have zero fight hits.

## Defeat transition

The accepted threshold is HP below 21, not HP zero. At HP 20 the overlay writes:

- `0x800823A0 = 1` at `0x800B3E70`;
- `0x80082470 = 150` at `0x800B3E7C`.

The retained full fight then reaches the level-complete screen. Later contacts are rolled back because the goal latch is already set.

*(Integration correction, 2026-08-03: the goal-latch writer PC was originally mis-cited as `0x800B3E6C`, which is actually the preceding `lui at,0x8008` half of the two-instruction store; the `sh` itself is at `0x800B3E70`. Re-verified against `tools/phase4_d19_molt.c`.)*

## Phase 4 boundary

D19 is `partial`, with high-value row-specific work bounded-exhausted. Charge/pursuit, guard rollback, crowd production, HP progression, and the victory handoff have exact original owners and pristine runtime evidence. Deferred work is exhaustive RNG/origin distribution, presentation-exact animation/GPU/audio timing, alternate death/restart breadth, and compiler matching. No new Interpreter movie or cold boot is currently required.

See [[EXP_2026-08-03_phase4_d19_molt]], `analysis/phase4_d19_molt.json`, `config/phase4_d19_molt.yaml`, and `tools/phase4_d19_molt.c`.
