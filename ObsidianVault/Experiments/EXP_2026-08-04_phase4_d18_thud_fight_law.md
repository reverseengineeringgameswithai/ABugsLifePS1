---
type: experiment
status: complete
date: 2026-08-04
system: Thud boss (Bug Bar)
phase: 4
artifacts:
  - analysis/phase4_d18_thud_fight_law.json
  - tools/phase4_d18_overlay_gate.c
  - tests/test_phase4_d18_fight.py
fixtures:
  - movies/Phase4/Interpreter/D18_thud_fight.movie.json
---

# Phase 4 D18/F09: the Thud fight law, writer-by-writer

## Question

D18's three named residuals, all blocked on a traceable fixture: who restores
the pool HP after each hit, who writes the final HP=0, and what does the
per-actor callback at +0x7C actually do?

## Fixture

The operator recorded `movies/Phase4/Interpreter/D18_thud_fight.movie.json`
— from-boot v4, 15,600 frames, boot → memory-card load → Bug Bar → Thud
defeated. Because it is **Interpreter-recorded**, instrumentation is free, so
every claim below is an attributed PC rather than an inference. Replayed on an
isolated instance with the operator's memory card **copied** as the seed (the
original was never written; hash verified before and after).

## The fight law (live, end-to-end)

| step | writer | effect |
|---|---|---|
| spawn | `0x80049CA0` `sh v0,0x6e(t0)` | pool HP := 50 at load (f5407) |
| hit | `0x800590E4` `sh v0,0x6e(s2)` | 50 → 48 (−2) |
| restore | **`0x800B3ED0`** (overlay) | 48 → 50, exactly two frames later |
| count | **`0x800B3DB0`** `sw v0,0x4cc8(at)` (overlay) | `0x800B4CC8` += 1 |
| kill | **`0x800B4528`** `sh zero,0x6e(s3)` (overlay) | pool HP := 0 at count 8 (f11880) |

Three findings follow:

1. **The pool HP field is a transient hit LATCH, not Thud's health.** The
   overlay restores it to 50 after every single hit. Anything reading
   `+0x6E` for this boss is reading a flag, not a health bar.
2. **The real fight counter is `0x800B4CC8`** — an overlay word incremented
   once per landed hit, running 0 → 8 across the fight, with the kill firing
   at exactly 8. This is the mechanical form of the long-standing "fight = 8
   perched berry hits" claim, which until now was an observational count.
3. **The damage itself is ordinary.** `0x800590E4` lies inside the committed
   `berry_tough_damage_dispatch` (0x8005905C), so the boss takes damage
   through the same berry law as any enemy; only the bookkeeping is special.
   The kill then hands off to the committed generic retirement path (actor
   removed from the live table 0x80090748, +0x5C bit 0x4000 cleared).

**The mover-VM stays parked throughout** — 1,644 IP writes during the fight,
every one of them by the VM interpreter's own store `0x8004C834`. This
confirms [[EXP_2026-08-03_phase4_d18_thud_vm_fsm]]'s FSM-negative on real
fight data, where it had previously rested on a poll-only replay.

## The callback at +0x7C is a sound cue, not a driver

`0x8004A0F4` is byte-matched C ([[FUNC_8004A0F4]], `thumper_driver_cb`). Its
entire body is:

```
lw   a1, 4(a0)        ; actor's position block
li   a0, 26           ; sound id
jal  0x8005044C       ; play_sound
addiu a1, a1, 4
```

So it plays **positional sound 26**; neighbouring stubs (`0x8004A11C` with id
125, etc.) are the same shape with different ids — a family of per-species
sound callbacks. **Correction:** D18/F09 described `+0x7C` as a "per-actor
driver callback", which implied behavioural control it does not exert.

## The "perched" qualifier, decoded

15 damage events produced only 8 counted increments. The qualifier turned out
to be **a position equality test against two hardcoded anchors** — so the
committed canon's word "perched" was literally correct.

`tools/phase4_d18_overlay_gate.c` locates the counter store's encoding inside
the overlay file (unique match), derives the load base from it, and
re-confirms that base against a second known PC. Result: the fight handler
lives in **`LEVEL04/LEVEL1.BIN` (4,924 bytes) loaded at `0x800B39A0`** —
confirming the committed overlay claim and adding its base. The handler reads:

```
0x800B3D3C  lh   v1,-530(0x800A0000)   ; Thud's pool HP (0x8009FDEE)
0x800B3D44  lw   v0,[0x800B4C70]       ; previous HP snapshot
0x800B3D50  beq  v0,v1  -> skip        ; no new damage
0x800B3D54  slti v1,21  -> skip        ; guard while HP < 21
0x800B3D60  jal  0x80050D1C (a0=93)    ; hurt SOUND      -- every hit
0x800B3D70  jal  actor_set_anim_sequence(actor,2,18)     ; hurt ANIM -- every hit
0x800B3D80  lw   v1,[0x800B4CB0]       ; the sweep position word
0x800B3D88  beq  v1,0xFFFD6E20 (-168416)  -> count       ; perch A
0x800B3D94  bne  v1,0x00026E20 (+159264)  -> DO NOT count ; perch B
0x800B3DB0  sw   v0,[0x800B4CC8]       ; counter += 1
0x800B3DB4  bne  v0,8                  ; at 8 -> kill path
```

**Live proof.** Breakpointing the predicate's own test instruction
(`0x800B3D88`) during the fight caught it evaluating **exactly 15 times** — one
per damage event — with **exactly 8 at a perch anchor**, and those 8 are
precisely the increments. Thud sweeps continuously between the two anchors;
only hits landed while he is stopped at an endpoint score.

Note the ordering: the hurt **sound and animation fire for all 15 hits**, so
the player sees every berry connect. Only the scoring is gated — which is why
the fight reads as "sometimes hits don't register".

**Modding consequence:** to shorten the fight, change the target literal `8`
at `0x800B3DA4` or relax the two anchors — **not** the pool HP, which is
restored after every hit.

## Damage response: three regimes, and a soft-lock

A/B poke experiment from **one** saved state (Thud parked at anchor −168416),
reloaded per trial so hit power is the only variable:

| delta from 50 | HP after | result |
|---|---|---|
| ≤ 29 | ≥ 21 | **counts**; overlay restores HP to 50 |
| 30–49 | 1–20 | **ignored, and HP is NOT restored** → the fight **soft-locks** |
| ≥ 50 | ≤ 0 | **instant retirement**, bypassing the 8-hit counter entirely |

The threshold is exactly the decoded guard: **HP 21 counts, HP 20 does not**.

The middle regime is the interesting one. The restore lives *inside* the
counted branch, so an ignored hit leaves the latch low — and every later hit is
then also below the guard. Verified: HP held at 5 for 720 frames with the
counter still 0, and three further −2 hits (5→3→1→−1) were all ignored. **Thud
becomes permanently unkillable** unless a hit pushes HP to ≤ 0, which retires
him through the generic path instead.

**Native reachability correction, 2026-08-04.** The *response* to a synthetic
30–49 delta remains proven by poke, but no native equipped berry can produce
that delta. The earlier reasoning confused mega's constructor type `45` with
damage. The constructor uses type 45 only to index its metadata row; the row's
damage selector is `128`, which `berry_tough_damage_dispatch` maps to exactly
−3. A fail-closed C pass checked all seven primary/child rows reachable from
the five equipped berries. Effective damage to Thud is limited to `{0,2,3,4}`:
red is blocked by the berry-tough reaction class, blue and green deal 2, mega
deals 3, and gold deals 4. Selector 1's −99 branch is not reachable from a
native equipped-berry row. Therefore the 30–49 soft-lock and ≥50 instant-
retirement regimes are **perturbation-only**, not original-game outcomes.

**Retirement rule re-confirmed:** HP ≤ 0 retires (0, −1, −5 all zero the live
slot and clear the active bit; 1 survives). An in-session worry that −1 failed
to retire was my own under-observation — I advanced only 12 frames and never
checked the live table. The committed phase3_thud rule stands unchanged.

## Why bursts collapse: a state change, not a cooldown

Three normal hits poked in rapid succession from a fresh anchor produced only
**one** count — because the first hit **sends Thud sweeping**. The gate word
moved −168416 → −153056 → −137696 → −122336 across the trials, so hits 2 and 3
were evaluated mid-sweep and failed the anchor test.

So the 15-events→8-counts collapse is not a refractory timer, which is what the
frame spacing first suggested. Being hit *at* an anchor changes his state, and
he is only scoreable again once he next comes to rest. That reproduces the
movie's burst structure exactly (bursts ≤48 frames wide, 370–1100 frames apart).

## Sweep ownership closure

The retail `LEVEL04/LEVEL1.BIN` overlay is hash-pinned at
`816667f0ba7ae2b602cc39da7c0b3b4020d1a231651d5b90e6374c66c34f39e6`.
A C census derives load base `0x800B39A0` from the already-attributed counter
and restore stores and finds exactly seven direct references to sweep word
`0x800B4CB0`. Its writers are initialization at `0x800B3B40` and the paired
update stores `0x800B4388` / `0x800B43A8`. The update instructions add or
subtract `0x0A00` and publish the resulting coordinate to actor field `+0x28`.
This closes the earlier owner question: the Bug Bar overlay drives the sweep;
the actor mover VM remains parked.

## Bounded disposition

**D18 is substantiated partial and bounded-exhausted.** Identity, native berry
damage, hit response, perch qualification, score count, restore/kill writers,
retirement, callback sound, parked-VM negative, and sweep ownership are now
instruction-bound. E11's arena visible-index mapping remains a separate row.
Remaining D18 work is perturbation-only malformed state, redundant runtime
reproduction of exact metadata, presentation cataloguing, or compiler-matched
overlay reconstruction. No new Interpreter movie is required to move on.

## Gates

`tests/test_phase4_d18_fight.py` — 15 tests: the damage writer lies inside the
committed berry dispatch (checked against `re_symbols.sym`); pool HP is a
latch; the counter reaches exactly 8 before the kill; the resident/overlay
writer split; the VM-parked invariant cross-checked against the prior D18
artifact; the callback is `play_sound`; an EXE spot-pin of the callback's instructions;
the qualifier's 15/8 split; the two anchor literals read back out of the
retail overlay bytes at the decoded sites; and the ungated-reaction /
gated-scoring ordering; the three damage regimes with the exact threshold; the
proven/unproven split in the soft-lock claim; the retirement rule; and the
burst-collapse mechanism. All pass.

## Related

[[SYS_thud_bug_bar_boss]] · [[EXP_2026-08-03_phase4_d18_thud_vm_fsm]] ·
[[EXP_2026-08-02_phase4_e11_dynamic_geometry]] · [[FUNC_8004A0F4]]
