---
kind: experiment
id: EXP_2026-08-03_phase4_d01_enemy_spawn_update
status: complete
source_state: original_game
system: [Enemy_spawn_architecture, SYS_enemy_death_and_permanence]
row: D01_enemy_spawn_update
---

# Phase 4 D01: general enemy spawn/update, synthesized from committed evidence

## Question

D01_enemy_spawn_update is the umbrella row: role binding for the census's 36 unknown-role
actor ids, the update scheduler, reset/respawn, lifecycle, and Thud's actor source. Like
D05 before it, the general row lagged far behind its own specific instances — a dozen
per-species Phase-4 rows plus D02/D05/E07/C04 have been answering exactly these questions
all session, without D01's own registry entry ever citing them. Zero new live work this
pass; committed evidence only.

## Scheduler and lifecycle, assembled

- **Pool init**: `0x8004A42C` clears exactly 64×`0x84` bytes and initializes active records
  (E07). **Program selection**: initializer `0x80049C30` — the sole resident reference to
  the 40-pointer mover-VM program table — reads metadata byte `+13`, writes actor `+0x70`.
- **Per-frame scheduler**: `0x8004D224..0x8004D6A4` loops the live pointer table
  `0x80090748` each frame — ticks each actor's `+0x4A` death-anim countdown, fires
  `FUNC_800498AC(actor, 1|2)` on zero-crossing, owns the conditional re-init call, and runs
  the camera-anchored admission check (D05's flagged direction-contradiction stands, not
  re-litigated).
- **Death/removal**: `FUNC_800498AC` `a1=2` clears the id and compacts `0x80090748` — a
  live-table index is not a stable identity. **Respawn**: from-scratch re-instantiation at
  `0x80049C2C` via backlink `+0x80` (D12/D05). **Quota**: computed at load by
  `FUNC_80046B20`'s pool scan (C04) — refining the archived page's older observation that
  adding a chunk-31 record raises the quota automatically.

## Pool-base reconciliation

Phase-1's census says records sit at "FIXED `0x8009FE04`"; every later row uses
`0x8009FD80`. Both are right: `0x8009FE04 = 0x8009FD80 + 0x84` — the census enumerated from
slot 1 of the same pool. Cross-check: D19's Molt at `0x8009FF90` = base + 4×`0x84`. Caveat
from committed D09: records are not always in this pool at all (Redbug's lived at
`0x800A095C`); the authoritative access path is the live pointer table `0x80090748`.

## Id roster: 17 of the 36 unknowns now bound

Joining the census against committed identity claims only (per-species artifacts, Canon,
and the committed archived `Enemy_spawn_architecture` page with its 44/44-verified
type-word-low-byte==id rule):

| id | species | source |
|---|---|---|
| 6 | Horsefly | D15 + archived table |
| 9 | spider (common chaser) | archived table + relocation/ADD POCs |
| 10 | mosquito | archived cross-level save table |
| 12 | grub (ex-"earthworm") | D11/D12 |
| 13 | internal "bee" = campaign wasp | D14 |
| 15 | grasshopper | SYS_bonus_unlock_challenges |
| 17 | huge_spider = daddy long legs | D15 |
| 18 | shell_bug | D13 |
| 19 | Redbug ("cockroach") | D09 |
| 22 | Hopper | D20 |
| 29 | Molt | D19 |
| 30 | bird (boss hp 50 / hazard hp 101) | D17/F04/F06 |
| 34 | dragonfly | D14 |
| 37 | mite (ex-"canyon_bug") | D11 |
| 39 | pill | archived table + POC |
| 40 | worm | D12 |
| 41 | wall_worm | D12 |

Plus Thud (`0x24`=36) **outside** the census set — consistent with the census's own finding
that Bug Bar authors zero chunk-31 records; Thud is live-table-sourced (phase3_thud), his
exact spawner being E11's active-row territory. 19 ids remain unknown-role
(0-5,7,8,11,20,21,23-28,32,35); several are likely non-enemy kinds sharing the pool (Dot
id 14 is the existing NPC counter-example). id 11 ("the large beetle" in D11's committed
text, present in nearly every level per the E07 stage-join census) is the strongest lead.

## id 11 characterized live (2026-08-03) — the last enemy-shaped unknown

Before declaring the row bounded, one short live pass closed the single remaining
enemy-shaped lead. `canyon_bug.sav`'s live table holds exactly one id 11 (`0x800A0B6C`):
**hp 1, no `+0x7C` callback, wander-only VM entry `0x8007755C`** (the same bytecode block
D14 documented for the dragonfly — entries share bytecode), and **flags `0x4030`**. That
flags value is decisive: bit `0x20` is exactly one of the bits C04's quota-scan exclusion
mask skips *and* one of the bits D14's homing-targetability filter rejects — **the game's
own code already classifies id 11 as not-a-real-enemy**, simultaneously excluding it from
the elimination quota and from homing-berry targeting. Type-word `0x040B` (low byte rule
holds); high bytes vary per level (`0x030B`/`0x000B` in LEVEL01), consistent with a generic
ambient-critter class with per-level variants. This also explains C04's low LEVEL01 quota
(4) despite many more live actors.

Bonus from the same table walk: the bird's backlink type-word read **`0x1A1E` directly**
(upgrading the earlier hedged inference to a direct read), and the mite case re-confirmed
the low-byte rule (`0x0125` → 37).

## What's still open

The 18 remaining unbound ids — none of which, after id 11's resolution, has any committed
evidence suggesting enemy-role status; binding them is per-id enumeration with no named
consumer. The actor-instantiation constructor PC (the archived page's own longest-standing
residual); Thud's exact spawner (E11); type-word high-byte semantics and the chunk-31 param
words; runtime record-slot mutation semantics; D05's admission-check contradiction.

## Evidence

`analysis/phase4_d01_enemy_spawn_update.json` (full citation list inside).
