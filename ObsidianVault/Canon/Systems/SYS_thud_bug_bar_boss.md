---
kind: system
id: SYS_thud_bug_bar_boss
name: Thud Bug Bar boss identity and retirement frontier
status: partial
confidence: partial
updated: 2026-08-02
---

# Thud Bug Bar boss identity and retirement frontier

On hash-verified pristine SCUS-94288 media in scene 14, the sole live enemy at the
Bug Bar arena is actor id 0x24. Its initial HP is signed s16 at actor +0x6E with
value 50; +0x5C carries berry-damageable bit 0x40 and active bit 0x4000. The actor
is driven by callback 0x8004A0F4 and mover-VM program pointer 0x800777A6.

Poke-falsification bounds retirement: HP 1 survives, while HP 0 retires. A
complete write log attributes the active-bit clear to mover_updater 0x8004D270
(sh v0,0(s1)) and the live-table slot clear at 0x80090748 to mover_updater
0x8004D43C (sw zero,0x748(at)). These are interior code sites, not callable ABI
boundaries; config/confirmed_sites.yaml owns their machine representation.

Authoritative evidence:

- analysis/phase3_thud.json — pristine live identity, HP A/B trial, paged write
  log, instruction PCs, save/media pins, and pre-load state inspection.
- config/record_types.yaml — actor field widths and unknown-byte accounting.
- config/confirmed_sites.yaml — typed retirement sites and MOD constraints.
- tests/test_phase3_thud.py — recomputes the bounded result.
- [[EXP_2026-07-13_thud_bug_bar_boss_binding]] — runtime experiment and method.

MOD consumption contract: an HP or relocation change must preserve signed +0x6E,
active bit 0x4000, live-table compaction/retirement, and mover-updater ownership.
Do not patch either interior store as if it were a continuation ABI. The rolling
arena's visible index mapping and the attack-phase mover-VM program remain partial.

## Phase 4 dynamic-geometry ownership refinement

The rolling arena code owner is no longer unknown. Player-facing stage 9 runs as
scene ID 14, so the relevant overlay is `LEVEL04/LEVEL1.BIN`, not the misleading
string-pool-associated `LEVEL08` lead. Its per-tick controller is `0x800B3C70`.

Static C/ASM reconstruction proves that controller performs three separate pass-2
geometry operations:

- `0x800B4550 -> 0x80029508` writes the XYZ transform for pass-2 object 9.
- `0x800B487C -> 0x800292DC` rotates objects 0 through 9. Their signed per-tick
  deltas are `[-100,+120,-90,+144,-110,+128,+32,+32,+32,+64]`.
- `0x800B49E0 -> 0x80029508` writes six interpolated paths for objects 0 through 5.

The leaf `0x80029508` is byte-matched C and writes XYZ into the selected pass-2
object's nested transform destination. A normal-speed Interpreter run from the
hash-pinned `level_09.sav` anchor recorded 61 controller ticks over 302 frames,
610 rotation calls, 427 transform calls, and 1,037 overlay-global writes with no
truncation. The controller ran exactly once every five emulator frames. A shorter
register capture proved object indices 0 through 9 and changing XYZ values directly.

This anchor is late-phase (`HP=0`), so it does not prove early/mid-fight state timing,
contact/damage behavior, post-fight reset, or which visible arena piece corresponds
to each pass-2 index. Those are the remaining E11 movie-gated claims. See
[[EXP_2026-08-02_phase4_e11_dynamic_geometry]].

## Pass2 authored-capacity boundary (2026-08-02)

Bug Bar's runtime scene 14 DAT (`LEVEL04/LEVEL1.DAT`) authors exactly ten non-null pass2 object slots with maximum index 9. This matches the boss controller's complete `0..9` rotation loop; its transform calls address object 9 and objects `0..5`. Across all 15 retail scene DATs, only scenes 3, 4, 14, and 15 contain non-empty pass2 tables, and those are exactly the overlays with direct calls to the shared pass2 geometry helpers. This is a bounded structural claim, not proof of each object's screen-visible identity or full boss lifecycle behavior. See [[EXP_2026-08-02_phase4_e11_dynamic_geometry]].

## The attack-phase mover-VM program: resolved NEGATIVE (D18/F09, 2026-08-03)

The long-open "attack-phase mover-VM program" does not exist. Corrections and
bounded findings, all double-checked against committed sources and live runs
(`analysis/phase4_d18_thud_vm_fsm.json`, `tests/test_phase4_d18.py`):

- **0x800777A6 is not a program entry** — it is the `jump_back` inside program
  #19 (`0x80077798`, parked idle). phase3_thud.json recorded it as Thud's LIVE
  VM IP; the registry transcribed the IP as a program address.
- **Thud's pool actor stays in the parked program for the entire fight** —
  poll-only replay of the operator fight movie (4113 frames): the IP never
  leaves the park loop, through a landed hit and through the actor's death.
  The sole +0x70 writer in instrumented idle runs is the VM interpreter
  itself (0x8004C834). Defeat (HP:=0) retires with NO death program switch;
  proximity triggers nothing.
- **The 0x800777xx block is a shared ambient bank**, not Thud logic: parked /
  stationary two-clip cycle / gated wander / wander / authored-path patrol,
  poke-verified behaviorally, used by ids 21, 7, 15, 22, 18 across level
  anchors (census +0x70 join).
- **Pool HP is the fight lane's hit latch**: a landed hit shows a transient
  50→48→50 dip (the committed −2-per-hit law), restored by the fight lane;
  at fight end the lane writes HP=0 and the generic retire path removes the
  actor. The restore/zero writers are unattributed — closing them needs a
  re-recorded Interpreter fight movie, the same fixture the E11
  dynamic-geometry row requests (one fixture closes both rows' remainders).

## The fight law, writer-by-writer (D18/F09, 2026-08-04)

The operator's Interpreter fight movie made the whole fight traceable. Every
writer below is an attributed PC (`analysis/phase4_d18_thud_fight_law.json`,
gated by `tests/test_phase4_d18_fight.py`):

- **spawn** `0x80049CA0` — pool HP := 50 at load.
- **hit** `0x800590E4` — 50 → 48 (−2). This PC is inside the committed
  `berry_tough_damage_dispatch` (0x8005905C): the boss takes damage through
  the ordinary berry law.
- **restore** `0x800B3ED0` (overlay) — 48 → 50, two frames after every hit.
  **Therefore the pool `+0x6E` field is a transient HIT LATCH, not health.**
- **count** `0x800B3DB0` (`sw v0,0x4cc8(at)`, overlay) — increments the real
  fight counter **`0x800B4CC8`**, which runs 0 → 8 across the fight.
- **kill** `0x800B4528` (overlay) — at counter 8, writes pool HP = 0, handing
  off to the generic retirement documented above (live-table slot zeroed,
  +0x5C bit 0x4000 cleared).

This gives the long-standing "8 perched berry hits" claim a mechanism: the
count lives at 0x800B4CC8 and the kill is gated on it. The mover-VM stays
parked for the entire fight (1,644 IP writes, all by the interpreter's own
store 0x8004C834), confirming the FSM-negative on real fight data.

**Correction:** the actor's `+0x7C` "driver callback" `0x8004A0F4` is
`thumper_driver_cb`, byte-matched C whose whole body is
`play_sound(26, actor position)` — a positional **sound cue**, not a
behavioural driver. Earlier row text implied control it does not exert.

### The "perched" qualifier is a two-anchor position test (decoded)

15 damage events produced 8 counted increments because the overlay gates
scoring on **position equality**: the sweep word `[0x800B4CB0]` must equal
exactly **-168416** (`0xFFFD6E20`) or **+159264** (`0x00026E20`) — Thud's two
perch anchors. He sweeps continuously between them, so only hits landed while
he is stopped at an endpoint count. The committed "8 perched berry hits"
wording was therefore literally accurate.

Handler (overlay **LEVEL04/LEVEL1.BIN**, 4,924 B, **load base 0x800B39A0** —
derived from the counter-store encoding and re-confirmed against the restore
store, `tools/phase4_d18_overlay_gate.c`): HP-edge detect against the snapshot
`[0x800B4C70]` → `HP < 21` guard → hurt **sound 93** and hurt **animation**
(`actor_set_anim_sequence(actor,2,18)`) which fire for **every** hit → the
perch test at `0x800B3D88`/`0x800B3D94` → counter `+= 1` at `0x800B3DB0` →
kill at 8.

Live proof: breakpointing `0x800B3D88` caught 15 evaluations, exactly 8 at an
anchor, and those 8 are the increments. Because the reaction is ungated while
the scoring is gated, the player sees every berry connect — which is why the
fight reads as "some hits don't register".

### Damage response has three regimes (poke A/B from one anchor state)

| delta from 50 | HP after | result |
|---|---|---|
| ≤ 29 | ≥ 21 | counts; HP restored to 50 |
| 30–49 | 1–20 | **ignored, HP NOT restored → fight soft-locks** |
| ≥ 50 | ≤ 0 | instant retirement, bypassing the counter |

The threshold matches the decoded `slti v1,21` exactly (HP 21 counts, 20 does
not). Because the restore sits inside the counted branch, an ignored hit leaves
the latch low and every later hit is also below the guard — verified by holding
HP at 5 for 720 frames (counter unmoved) and landing three further −2 hits, all
ignored. **A berry delivering a 30–49 delta would make Thud unkillable.**
Whether any real berry does so is **untested**: committed canon puts mega at
power 45, but the fight movie only produced −2 and −4, and it is unproven that
`berry_tough_damage_dispatch` passes full power to a berry-tough boss.

Retirement re-confirmed against the committed rule: HP ≤ 0 retires, 1 survives.

### Bursts collapse because a hit starts his sweep

Three rapid hits from a fresh anchor produced one count: the first hit sends
Thud sweeping (gate word −168416 → −153056 → −137696 → −122336), so the rest
are evaluated mid-sweep and fail the anchor test. The 15→8 collapse is a state
change, not a cooldown timer.

**MOD note:** shorten the fight via the target literal `8` at `0x800B3DA4` or
by relaxing the anchors — never via pool HP, which is restored each hit, and
beware that boosting berry power past a 29 delta breaks the fight rather than
speeding it up.

See [[EXP_2026-08-04_phase4_d18_thud_fight_law]].
