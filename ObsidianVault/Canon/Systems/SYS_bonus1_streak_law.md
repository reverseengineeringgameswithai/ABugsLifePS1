---
kind: system
id: SYS_bonus1_streak_law
name: Bonus-1 streak law -- what counts, what resets, what is ignored
status: live_confirmed
confidence: confirmed
source_state: original_game
functions:
  - FUNC_8004ABF4
memory:
  - MEM_800A6500
evidence:
  - EXP_2026-08-04_phase4_f16_f18_bonus_stage
  - analysis/phase4_F16_streak_live.json
src_paths:
  - tools/phase4_f16_streak_law.c
  - tools/phase4_f16_streak_reset_trace.py
  - tests/test_phase4_f16_streak_law.py
patch_policy: safe_to_read
---

# SYS_bonus1_streak_law

The complete rule for the Bonus-1 chain counter `0x8008223C` (= `gp+1188`; `$gp` is
the proven constant `0x80081D98`). Companion pages:
[[SYS_bonus_unlock_challenges]] for the three challenges, [[SYS_bonus_stage]] for
where a completed challenge takes you.

## Two corrections this page exists to carry

1. **It is not about spiders, or about any species.** In the contact resolver
   `0x8004ABF4`, `s6` is set **once** at `0x8004AC78` to `0x800A6500 + 122 =
   0x800A657A` — the **player** struct — and is never reassigned inside the
   per-actor loop. Every test that decides the chain reads *player* state at the
   instant of contact. Nothing looks at which enemy it is. The row was named
   "consecutive spider bounces"; that described the recording, not the rule.
2. **A berry throw resets the chain, whether or not it kills anything.** The clear
   sits at the *entry* of the berry constructor, before anything can hit anything.

## Resolved direct counter sites

**Correction history.** This section formerly said "the counter's domain is closed"
and called the list complete across the resident EXE and all overlays. That exceeded
the fixed-form scan. It resolves **eight direct resident sites**: one read, one
increment, and six clears; it finds no fixed-form direct overlay hit. The resident
census still carries 12,956 unresolved-base accesses (44 same-width sites in related
functions) and 149 unresolved indirect calls, while overlay scans retain their own
unresolved-base class. The table is the resolved direct set, not an absolute domain.

| PC | function | effect |
|---|---|---|
| `0x8004B38C` | `actor_player_contact_resolver` | the only read |
| `0x8004B3A8` | `actor_player_contact_resolver` | **the only increment** |
| `0x800470D8` | `berry_throw_dispatch` | clear |
| `0x8004A6C4` | `object_slot_type_init` | clear |
| `0x8004A854` | `resident_level_transition_initiator` | clear |
| `0x8004B1D4` | `actor_player_contact_resolver` | clear |
| `0x8004B350` | `actor_player_contact_resolver` | clear |
| `0x8004B3D0` | `actor_player_contact_resolver` | clear after the fifth |

## The three-way test on player `+0x84`

The crux is one instruction, `sltiu` at `0x8004B2B4`, which is easy to read past as
an ordinary comparison. The field is `0x800A6584` (player `+0x84`), loaded **`lhu`**
— unsigned:

```
v = (unsigned halfword)[0x800A6584]
  v >= 2   ->  branch to 0x8004B67C, the function tail
               the counter is NEVER touched -- neither counts nor resets
  v == 1   ->  0x8004B35C, the counting block
  v == 0   ->  0x8004B350, CLEAR
```

The branch target `0x8004B67C` is past every write to the counter, so "≥ 2 is inert"
is a structural fact, not an observation. This one field is the whole of "some
contacts break the chain and some don't" — it is not two separate rules.

⚠️ **The unsigned load is not incidental.** The live capture showed `0x800A6584` is
not a small enumeration: over one recording it took `0..10` *and* a run of negative
values (`-6144 .. -512`, in steps of 512). Because the gate is `lhu` + `sltiu`,
every negative value reads as a very large unsigned number and lands in the **inert**
bucket. A signed reading of this test gets the behaviour backwards over a large part
of the field's real domain.

### `0x800A6584` is the butt-slam window timer

That odd domain is what identified it. It is not a class — it is a countdown, driven
entirely from `player_vertical_update` (`0x80048138`):

| PC | what it does |
|---|---|
| `0x80048C74` | requires player action state `0x800A6580 == 2` |
| `0x80048C8C` | requires height `[player+0x48] - [player+0x04] >= 8193` |
| `0x80048C9C` | plays sound 27 |
| `0x80048CA8` | **timer := 10** |
| `0x80048CBC` | player state `0x800A6580 := 4` — Canon's slam/dive |
| `0x80048D98` | `blez` — a timer at or below 0 is left alone |
| `0x80048DA4` | **if the timer is 1 it is NOT decremented**; instead `[0x800A6530] := 4096` |
| `0x80048DB8` | otherwise decrement by 1 |
| `0x80048DD4` | a negative timer climbs by **+512** per frame back toward 0 |
| `0x80048DF8` | sets the timer to `-6144` |

So the timer runs `10 → 1` over the entry frames and then **sticks at 1** for the
whole descent, re-applying velocity `4096` every frame. `1` is therefore not a
one-frame edge — it is the sustained slam.

Which makes the three-way test read in plain terms:

- **timer `== 1`** → the player is in a sustained butt-slam → the contact **counts**;
- **timer `== 0`** → the player is not slamming at all → the contact **resets** the
  chain;
- **timer `2..10`** (the entry frames) or **any negative value** (the recovery
  window, ~12 frames climbing back to 0 in 512s) → the contact is **inert**, neither
  counting nor resetting.

That is the mechanism behind "some things reset it and some things don't": it is not
a property of the attack or of the enemy, but of *where the player is in the slam
timer* when the contact resolves.

Consistent with the field's other uses: [[SYS_berry_projectile_and_homing]] treats
`+0x84 != 0` as a berry-throw denial, and `FUNC_80054C90` requires `+0x84 == 0` to
take a checkpoint — both are "not mid-slam" tests.

## Every way the chain dies

- **Throwing a berry** — `0x800470D8`, **unconditional** at the entry of
  `berry_throw_dispatch` (`0x800470AC`). Proven both ways: no branch exists in
  `[0x800470AC, 0x800470D8)`, and nothing anywhere in the function branches over
  the store. Its sole caller `0x80049094` fires when the berry action state
  `0x800A6586` reaches `10`, which [[SYS_berry_projectile_and_homing]] establishes
  is the berry **constructor**. ⚠️ Therefore the *throw* ends the chain — a berry
  thrown at empty air still ends it.
- **A contact while any of these hold** — `0x8004B1D4`:
  `0x800A657A == 12` (the carried-object gate) · `0x800A6590 & 0x80` (power word) ·
  `0x800A6588 == 13` (mode/anim index).
- **A contact with class 0** — `0x8004B350`.
- **A level load or scene transition** — `0x8004A6C4` (`object_slot_type_init`,
  reached straight off the 64-actor loop, unconditional) and `0x8004A854`
  (`resident_level_transition_initiator`). The chain does not survive either.
- **The successful fifth** — `0x8004B3D0`, which resets to 0 after firing.

An actor whose flags `[actor+0x5C] & 0xC0` are set is skipped before any of this
(`0x8004B194` → `0x8004B3DC`), so such a contact neither counts nor resets.

## Counting

Guarded at `0x8004B35C..0x8004B3D0`:

- skip entirely if the earned bit `0x20` is set in `0x8009B889` (`0x8004B36C`), or
  if the scene is `0x10`, i.e. already inside the bonus stage (`0x8004B384`);
- `0x80082444 := count + 114` — the progress command, `114..118` for steps 1..5;
- threshold is **5** (`0x8004B3A4`). The fifth ORs low bit `0x02` into the flags,
  sets transition latch `6` and fade `30`, then clears the counter.

## Measured, action by action

The operator recorded `movies/Phase4/Interpreter/Bonus01_Counter_ResetTest.movie.json`
specifically to test this, with six different kills/events and an explicit warning
that some of them might not reset anything. Replayed with a write watch, every
counter event attributed to its PC, and frames converted to movie-relative (the
recording is state-anchored at emulator frame 10757 — comparing raw emulator frames
against the operator's marks would line every event up against the wrong action):

| operator's action | ~movie frame | counter event | verdict |
|---|---|---|---|
| berry kill | 515 | `0x800470D8` at **428** | **RESETS — at the THROW** |
| kick kill | 1150 | *none within ±200 frames* | **does not reset** |
| butt-slide kill | 1730 | `0x8004B1D4` at **1730** | **RESETS** |
| thrown-seed kill | 2600 | *none within ±200 frames* | **does not reset** |
| death | 3550 | `0x8004A854` at **3552** | clears (chain already 0 there) |
| landing-jump kill | 4060 | `0x8004B350` at **4065** | **RESETS** |

**The berry timing is the proof, not just a confirmation.** The clear landed at frame
428 and the kill at roughly 515 — about **87 frames, ~1.5 s, before** the berry hit
anything. The chain was already dead when the berry was still in the air. "Berry
kills reset the chain" is therefore the wrong causal model; the throw does it, and
the tool's static prediction is what the recording bears out.

**A thrown seed does not go through the berry path.** It produced no counter event at
all, so seed throws and berry throws are not the same dispatch.

**Taking damage clears it too.** `0x8004A854` fired five times in that run — 1420,
2000, 3188, 3320, 3552 — destroying live chains at 1420 and 3188. ⚠️ The function
census names its container `resident_level_transition_initiator`, but the block the
clear sits in is unmistakably the player **hit/knockback** path: it plays sound 14,
writes stun `-30` to `0x800A6592`, reads health `0x800A6594`, sets state 5, applies
velocity `-1024`, and zeroes the slam timer, the grounded flag `0x800A6582`, the
berry action state `0x800A6586` and the latch `0x800A659E`. Firing five times
mid-level is consistent with taking hits, not with level transitions. Treat the
census name as not describing this block.

## Verified

43 static pins (`tools/phase4_f16_streak_law.c`, `-Werror`, including the
fixed-form direct scan over all 22 images) plus a live replay of the operator's
`movies/Phase4/Interpreter/F16_Bonus01.movie.json` — **format v4,
Interpreter-recorded**, so writes are attributed to the PC that made them. That run
produced five increments at `0x8004B3A8` (values 1..5), the unlock, and **no observed
writer outside the resolved set in that run**.

⚠️ Scope of the live evidence: that recording is a clean run, so it exercises the
counting side and the success reset only. The reset causes above are proven
statically; the berry reset in particular carries a falsifiable prediction — slam
two or three targets, throw a berry at nothing, and the next slam should count `1`.
