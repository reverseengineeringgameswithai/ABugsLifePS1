---
type: experiment
status: complete
date: 2026-08-03
system: Thud boss (Bug Bar)
phase: 4
artifacts:
  - analysis/phase4_d18_thud_vm_fsm.json
  - tools/phase4_d18_thud_vm_fsm.py
  - tests/test_phase4_d18.py
---

# Phase 4 D18/F09: Thud's "phase/attack mover-VM FSM" — resolved by falsification

## Question

D18 and F09 shared the item: "Decode the mover-VM program at 0x800777A6 for
Thud's phase/attack FSM."

## Answer (short)

**There is no such FSM.** Two corrections and a bounded negative:

1. **0x800777A6 is not a program entry** — the committed 40-entry program
   table has none there; it is the `jump_back` inside program #19
   (0x80077798, parked idle). `phase3_thud.json` recorded it as Thud's LIVE
   VM IP and the rows transcribed the IP as if it were a program.
2. **Thud's pool actor never leaves the parked program** — through the whole
   operator fight movie (4113 frames, poll-only), through a landed hit, and
   through its own death.
3. The 0x800777xx block is a **shared ambient program bank** (census join:
   ids 21, 7, 15, 22, 18 use its five programs at various level anchors) —
   nothing Thud-specific.

## Method and results

- **Synthesis**: programs #19..#23 extracted from the committed E07 corpus
  (all instructions individually CONFIRMED there); phase3_thud.json supplied
  the live binding (slot 0, id 36, HP 50, cb 0x8004A0F4, IP 0x800777A6).
- **Idle watch** (isolated instance port 23702, thud_boss_movie.movie.sav,
  600 frames): IP oscillates 0x800777A4↔0x800777A6; the **sole +0x70 writer
  is the VM interpreter itself** (0x8004C834; 120/120 writes).
- **Program-semantics pokes** (fresh state per trial, +0x70 := entry, 240
  frames): #19 parked (no motion), #20 stationary two-clip cycle (no motion),
  #21 **gated** wander (rests at `park_arrive_test`), #22 wander (moved
  [2838,0,23125]), #23 authored-path patrol (moved [19403,1808,45836]).
- **Defeat poke** (HP:=0): zero guest writes to +0x70 afterward — retirement
  is immediate (active bit cleared, live slot zeroed), **no death program**.
- **Proximity** (Flik at 3000 units): no program switch; the +0x5C churn
  writers (0x8004D270 clear / 0x80024E58, 0x8004D38C restore) are a per-tick
  cycle, not aggro.
- **Fight replay, poll-only** (CachedInterpreter-era movie — never armed):
  138 samples over 4113 frames. IP: only the park pair. HP: 50 throughout,
  EXCEPT a transient **50→48→50 dip at ~frame 2910** (a landed hit's −2,
  matching the committed −2-per-hit KO-memory law from the E14 save-schema
  work, immediately RESTORED by the fight lane) and a terminal **HP:=0 at ~3870**
  (the fight lane kills via the generic HP-retire path).

## Correction discipline note

An initial summary claimed "HP never changes during the movie." The test
gate's assert against the saved timeline caught this same-session: the full
timeline contains 48 and 0. The corrected reading (transient hit latch +
terminal zero) is *stronger* evidence for the verdict — the VM stays parked
even while the actor is hit and killed.

## Consequences

- D18's and F09's shared next is **answered**: the fight's phase/attack
  behavior belongs to the overlay lane (LEVEL04/LEVEL1.BIN controller canon,
  perched-hit fight law), not to a pool-actor VM program.
- Named reopeners (both need one re-recorded **Interpreter** fight movie —
  the same fixture E11's movie-gated items already request): attribute the
  driver callback 0x8004A0F4's per-tick role; attribute the pool-HP restore
  writer and the final HP=0 writer.

## Gates

`tests/test_phase4_d18.py` — 5 tests: offline sections regenerate from
committed sources; the address correction holds against the committed table;
IP-parked-through-hit-and-death invariant; poke semantics consistency;
census shared-bank join. All pass.

## Related

[[SYS_thud_bug_bar_boss]] · [[EXP_2026-08-02_phase4_e11_dynamic_geometry]] ·
[[SYS_actor_model_loading]] (id 36 = chars3\thud)
