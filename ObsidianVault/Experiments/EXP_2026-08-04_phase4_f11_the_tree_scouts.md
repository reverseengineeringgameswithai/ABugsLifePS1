---
kind: experiment
id: EXP_2026-08-04_phase4_f11_the_tree_scouts
status: complete
source_state: original_game
system: [SYS_cinematic_camera, Dot_guide_NPC]
row: F11_the_tree
---

# F11 (The Tree): the scout-found progression

The row was `external_lead` with two bindings, and its own `next` was concrete:
*"Diff the LEVEL11_1-5 saves to locate the scout-found progression state."* That is offline,
deterministic work needing no new recording, so it went first.

## The diff

`tools/phase4_f11_scout_progression.py` loads each of the five saves, dumps all 2 MiB of RAM, and
ranks addresses that move **monotonically** across 1 → 5 with small bounded values.

All five saves are scene 12 with strictly increasing frame counters (185909 → 197427), so they are
genuinely progressive snapshots of one playthrough.

**59 monotonic candidates. Exactly one has a small bounded value:**

| address | width | values across saves 1→5 |
|---|---|---|
| **`0x800B4A48`** | u32 | **5, 4, 3, 2, 1** |

## ⚠️ Which blob — the scene-asset name is wrong again

`0x800B4A48` is in **region A**, the shared overlay swap buffer, so the value means nothing without
knowing which blob is loaded. The row's own binding says scene 12 → *"overlays
LEVEL03_LEVEL/_LEVEL1"*, taken from the scene-asset graph.

**That is not the resident blob.** Comparing a 1 KiB *code* window at `0x800B4400` against every
candidate, in both `LEVEL11_1.sav` and `LEVEL11_5.sav`:

| blob | match |
|---|---|
| **`LEVEL02/LEVEL1.BIN`** | **100.0 %** |
| `LEVEL07/LEVEL1.BIN` | 16.0 % |
| `LEVEL09/LEVEL.BIN` | 10.8 % |

This is the **second row today** where the asset-graph directory name is not the blob that runs —
the Council Chamber (D16/F03) was the first, where scene 2 runs `LEVEL02/LEVEL.BIN` rather than the
`level03\level1b` the graph names. Treat the graph as naming *assets*, not the executing overlay.

A code window is used deliberately rather than a hash of the region head: overlays mutate their own
first bytes at runtime, so a head hash reads as unrecognised mid-level.

## The mechanism

`tools/phase4_f11_static.c` — 19/19 pins against `LEVEL02/LEVEL1.BIN`.

**A scout is "found" when its actor flags (`+0x5C`) carry bit `0x1000`.** Each tick the overlay walks
the scouts and counts them:

```
0x800B42A0  andi v0,v0,0x1000       ; found?
0x800B42A4  beq  -> 0x800B4324      ; not found: skip WITHOUT counting
...                                 ; found, first time:
0x800B42D4  20(sp) = 2              ;   cinematic-camera FLAGS = 2
0x800B42D8  a0/a1/a2 = [s0+0/4/8]   ;   the scout's own position
0x800B42F4  [0x800B4A4C] = 300      ;   a 300-frame timer
0x800B42F8  jal 0x8004DA94          ;   START THE CINEMATIC CAMERA there
0x800B4318  jal 0x8005044C          ;   play_sound(-13, scout)
0x800B4320  s3++                    ; counted
```

then publishes the remaining count:

```
0x800B44A4  v0 = 5
0x800B44B0  subu v0,v0,s3           ; 5 - found
0x800B44B8  [0x800B4A48] = v0       ; *** SCOUTS REMAINING ***
```

So the counter is **derived, not decremented** — which is why it reads a clean 5,4,3,2,1.

Three further details:

- **The found bit is PERSISTENT** — corrected below; an earlier draft called it a one-shot.
- **Init is 6, not 5** (`0x800B3CAC/B4`), so "none found yet" is distinguishable from "five left".
- **A per-count audio cue**: a byte table at `0x800B49EC` is indexed by the remaining count and fed
  to `sfx_dispatch` `0x80050994` (`0x800B458C..0x800B459C`) — a different sound per scout.

**Finding a scout starts a cinematic camera at that scout's position** — the same
[[SYS_cinematic_camera]] system D16/D17 documented today, with the same `flags = 2`. That is now
three independent uses of one mechanism (Thumper defeat, bird defeat, scout found).

This blob is also the one the D16 census flagged as the single *overlay* reader of `0x80090BEE`
(`0x800B4560`, `andi 1`) — it gates part of its own logic on the cinematic camera being active.

## The find event, traced

The operator recorded `movies/Phase4/Interpreter/F11_scouts.movie.json` (4,605 frames, format v4,
starting **before** the level loads so the overlay init is captured too).
`tools/phase4_f11_find_event.py` watches the five scout flag words — addresses taken off the counting
loop itself, not assumed — plus the counter. Ring not truncated.

**Two finds, one setter PC:**

| scout | frame | flags | PC |
|---|---|---|---|
| 0 | 9481 | `0x4085` → `0x5085` | **`0x8004B464`** |
| 1 | 10880 | `0x4085` → `0x5085` | **`0x8004B464`** |

and the counter walked **6 → 5 → 4 → 3** — init 6, then `5−0`, `5−1`, `5−2`. The derivation is
confirmed live.

**`0x8004B464` is inside `actor_player_contact_resolver` (`0x8004ABF4`)**: `ori v0,v0,0x1000` on the
touched actor's flags. **Finding a scout is touching it.** That is generic resident contact code, not
scout-specific — so bit `0x1000` means *"the player has contacted me"* campaign-wide.

That also settles a question I explicitly left open: the mosquito species callback (D16) tests and
consumes the same bit. It is **one shared convention**, not a coincidental reuse of a spare bit —
the contact resolver sets it, and each species decides what to do about it (the mosquito consumes it
and rises; the scout counter just counts it).

## The exit gate — the objective, closed

Second recording: `movies/Phase4/Interpreter/Any% Runs/LEVEL11_THETREE.movie.json` (12,107 frames),
collecting all five and exiting. Ring not truncated, 33,813 events.

**All five finds, one PC** (`0x8004B464`), **zero clears**, and the counter walked the full
**6 → 5 → 4 → 3 → 2 → 1 → 0**. It reached 0 at frame **121088**; the goal latch was set to 1 at
frame **122218** by `0x800B4424` — 1,130 frames later, which is the walk to Dot. Scene id then goes
12 → 0 at 122517 via `scene_setup_and_load` `0x800503AC`.

The gate itself:

```
0x800B43EC  lhu  v0,0x5C(s1)          ; s1 = 0x800A1850 = DOT
0x800B43F4  andi v0,v0,0x1000         ; has the player CONTACTED Dot?
0x800B43F8  beq  -> 0x800B44A4        ; no -> skip (that path CLEARS Dot's bit)
0x800B43FC  v0 = 5
0x800B4400  bne  s3,v0 -> 0x800B4458  ; *** not all five -> REFUSE ***
0x800B440C  lh   v0,[0x800823A0]
0x800B4414  bne  v0,zero -> 0x800B4458; already latched -> once-only
0x800B4424  sh   v0,[0x800823A0]      ; *** THE LEVEL EXIT ***
```

`s3` is the same live count of scouts carrying the contact bit, so `bne s3,5` is literally *"you
have not found all five."* The operator described this exact behaviour before the recording —
*"less than that and touching Dot will not take you out of the level"* — and this is that sentence
as an instruction.

**The gate actor is Dot, measured not assumed**: reading `0x800A1850`'s record live gives id **14**,
matching this row's existing Dot binding (Canon `dot-guide-npc`, chunk-31 id 14).

## ⚠️ Correction, now fully resolved: which actor's bit is the one-shot

An earlier revision claimed the *scouts'* found bit is a one-shot cleared at `0x800B449C`. Wrong
actor, right instruction. `s1` is reassigned at `0x800B4340/44` to `0x800A1850` — **Dot** — before
that clear. So:

- **the scouts' contact bits are PERSISTENT** (zero clears across all five finds, both recordings),
  which is what makes `5 − count` stable;
- **Dot's contact bit is the one-shot**, consumed at `0x800B449C` so that each touch is one attempt.

The original static reading tracked the offset but not the base register's reassignment.

## Incidental cross-check

Scout actors carry `+0x6E` = **101**. Per D17's damage table the gate at `0x80059068` is
`slti v0,v0,100`, so a target with HP ≥ 100 never reaches the damage table — **scouts are
undamageable**, by the same mechanism that makes the Cliffside bird invulnerable.

## The overlay's complete state surface — and what that says about acorns

A dataflow scan of `LEVEL02/LEVEL1.BIN` shows the overlay stores to **exactly eleven** absolute
globals in `0x800B3000..0x800B6000`: `0x800B4A24`–`0x800B4A4C`. `tools/phase4_f11_overlay_state.py`
watches all eleven across the full Any% run (12,107 frames, ring not truncated, none silent):

| address | behaviour | reading |
|---|---|---|
| `0x800B4A24` | 0…4076, step 28, 1461 writes | 12-bit angle accumulator |
| `0x800B4A28` | 0/1/2, 21 writes | a small mode/phase |
| **`0x800B4A2C`** | **0,1,2,3,4 at frames 113743/115081/117200/118751/121088** | **the found-scout ordinal** — those are exactly the five find frames |
| `0x800B4A30` | 400…916, step 12 | a ramp |
| `0x800B4A34` | 0…4088, step 8, 4339 writes | 12-bit angle accumulator |
| **`0x800B4A38`** | `0x800A119C`, `0x800A1220`, `0x800A12A4`, `0x800A1328`, `0x800A13AC` | **the found scout's ACTOR POINTER** — an exact match for `0x800A119C + n·0x84` |
| `0x800B4A3C` | 92 → 0, one per two frames | countdown timer |
| `0x800B4A40` | 149 → 0 | countdown timer |
| `0x800B4A44` | 116 → 0 | countdown timer |
| `0x800B4A48` | scouts remaining | known |
| `0x800B4A4C` | 300 → 0 | cue / post-find timer |

So the stage overlay's entire state is: **the scout system, three countdown timers, and cinematic-camera
bookkeeping.** Nothing else.

### ⛔ Acorns are not a counted objective in this stage's overlay

**There is no acorn counter.** The eleven words above are the complete set the overlay writes, and
every one is accounted for. Combined with the save diff — which produced 59 monotonic candidates
across the five progression saves and exactly one small bounded counter, the scout one — that is a
reasonably strong negative.

⚠️ **Bounded, not absolute.** This rules out *overlay state*. It does not rule out acorns being
handled by generic **resident** systems (the way grain and FLIK letters have their own rows), or
being pure scenery/hazards with no counter at all. The row's name may simply be describing stage
features from a walkthrough rather than tracked objectives.

## Acorns — they exist, and they are reusable props

`tools/phase4_f11_actor_census.py` walks chunk-31 the way the game's own dispatcher does and joins
each species against E05's id→model table. **The Tree holds 57 actors across 10 species:**

| species | count | model |
|---|---|---|
| 9 | 11 | `chars\badbug` (spider) |
| 10 | 15 | `chars\mos` (mosquito) |
| 11 | 7 | `bits\seed` |
| 13 | 6 | `chars\wasp` |
| 14 | 1 | `chars2\dot` — **Dot**, confirming the gate actor |
| **31** | **7** | **`chars3\acorn`** |
| 32 | 5 | `chars3\bluescot` — **the scouts** |
| 33 / 35 / 4 | 1/1/3 | `chars3\fdim`, `chars3\flikharv`, `chars\rosie` |

So **acorns exist**: seven actors, `hp = 101` — which by D17's damage gate (`slti v0,v0,100`) makes
them **undamageable**, exactly like the scouts.

### They are not collectibles

Watching all seven across the full Any% run: bit `0x1000` is set **ten times across six of the seven**,
and **cleared every time**. Both halves matter:

- **the setter is `0x800B41A4` — overlay code, not** the resident `actor_player_contact_resolver`
  `0x8004B464` that marks scouts and Dot. Its condition is `(flags & 0x4001) == 0x4001`, i.e. the
  acorn's *own* state, not the player's proximity;
- **the clearer is `0x80049CAC`, inside `mover_init_from_record`** — the actor re-init. So each
  acorn is re-initialised after use;
- individual acorns fire **repeatedly** (acorn3 three times, acorns 2 and 5 twice each).

Set-by-overlay, cleared-by-re-init, repeatable, and **counted by nothing** — the overlay's complete
eleven-word state surface has no acorn field. That is the signature of a **reusable interactive
prop**, not a collectible.

### ⚠️ This qualifies an earlier claim of mine

Banking the scouts, I wrote that bit `0x1000` means *"the player has contacted me" campaign-wide* —
**one shared convention**. The acorns show that is too strong: the same bit is set here by *overlay*
code on its own predicate, with no player contact involved. Bit `0x1000` is a **shared scratch flag**
that the resident contact resolver uses for player contact and overlays reuse for their own
per-tick bookkeeping. The scouts/Dot findings are unaffected — their setter really is the contact
resolver — but the generalisation to "campaign-wide meaning" does not hold.

## The acorn state machine — a retirement path

`LEVEL02/LEVEL1.BIN` `0x800B41A8..0x800B4220`, with `a0 = acorn + 0x62`:

```
lw   v0,-6(a0)                  ; the word at acorn+0x5C
andi v0,v0,0x5000
bne  v0,0x1000 -> 0x800B4224    ; require MARKED (0x1000) and 0x4000 CLEAR
lh   v0,0x0C(a0)                ; acorn+0x6E (HP)
beq  v0,zero  -> 0x800B4224     ; already retired -> skip
...  walk the live actor table 0x80090748 looking for THIS acorn ...
beq  s3,-1    -> 0x800B4224     ; FOUND in the table -> skip
sh   zero,0x0C(a0)              ; +0x6E := 0
sh   zero,-8(a0)                ; +0x5A := 0
sh   5,0(a0)                    ; +0x62 := 5
```

**An acorn that has been marked and is no longer present in the live actor table gets retired.**

The condition looked at first as if it could never hold — the *setter* requires bit `0x4000` set,
while this branch requires it clear. The run settles it: acorn flags pass through **`0x1040`** and
**`0x1041`**, both of which satisfy `(flags & 0x5000) == 0x1000`, so the path is live.

Measured (`tools/phase4_f11_acorn_state.py`, same recording, ring not truncated) against a
deliberately falsifiable prediction — *"if no acorn's `+0x6E` goes to 0 from `0x800B4218`, or `+0x62`
never becomes 5 from `0x800B4220`, the reading is wrong"*:

**10 retirements across acorns 0,1,2,3,5,6**, `+0x6E → 0` from `0x800B4218` and `+0x62 → 5` from
`0x800B4220`, always paired, `+0x62` taking no other value on that PC. Exactly as predicted.

Together with the earlier finding — bit set by overlay `0x800B41A4`, cleared by
`mover_init_from_record` `0x80049CAC` — the full acorn cycle is: **marked → leaves the live actor
table → retired → re-initialised → available again.** That is what makes them *reusable* props, and
it is why nothing counts them.

## Not established

- The stage's own critical path/route (no pass has addressed it).

## Reproduce

```
tools/phase4_f11_scout_progression.py --port 23741     # the save diff
cc -O2 -std=c11 -Wall -Wextra -Werror tools/phase4_f11_static.c -o /tmp/f11 \
  && /tmp/f11 REBUILD/files/LEVEL02/LEVEL1.BIN
pytest tests/test_phase4_f11_the_tree.py -q
```
