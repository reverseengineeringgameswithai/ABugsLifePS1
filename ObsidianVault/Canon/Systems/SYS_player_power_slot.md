---
kind: system
id: SYS_player_power_slot
name: Player power slot 0x800A657E (invincibility / bubble shield)
status: confirmed_mechanism_partial_rows
confidence: confirmed
source_state: original_game
memory:
  - MEM_800A6500
functions:
  - FUNC_8004A700
  - FUNC_80048138_player_vertical_update
  - FUNC_800586B0_contact_-_pickup_walker
  - FUNC_80051DBC_harvester_equip_and_active_update
  - FUNC_8005B134_respawn_transition_state_handler
  - FUNC_8004ABF4_proximity_updater_8004abf4
evidence:
  - EXP_2026-08-01_phase4_b06_b08_power_slot
  - analysis/phase4_b06_b08_powerups.json
src_paths:
  - tools/dis_exe.py
rows:
  - B06_invincibility
  - B08_bubble_shield
patch_policy: safe_to_read
---

# SYS_player_power_slot

> **Scope of this note.** The *mechanism* below is confirmed and independently
> re-derivable from the pristine EXE. The *rows* it serves — `B06_invincibility` and
> `B08_bubble_shield` — are **partial**, not solved: they were promoted on 2026-08-01
> and retracted the same day against the strict Definition of Done.
>
> **Current scorecard (2026-08-01, after adversarial review): MET 1, 3, 6, 7, 8 ·
> ADVANCED 2, 4, 5, 9.** Items 2, 4, 5 and 9 were briefly graded ✅ and the review
> downgraded them. The then-unexercised exceptional path was later shown not to touch
> this slot at all; item 4 remains advanced pending a re-derived exceptional-path list.
> The other review reasons remain: enumerating a residual is not bounding it, an
> inherited gap is still a gap, and the evidence wrapper lacks required provenance. See the DoD table in
> [[Phase 4 - Solve Every Gameplay and Engine Subsystem]], and read "Not established"
> at the bottom before consuming this as closure.

## Confirmed pristine behavior

`0x800A657E` (player block `+0x7E`, **signed** halfword) is a **single slot carrying
two different power-ups**, selected by SIGN — and the *consumption rule* follows the
sign:

| slot | power | consumed by | row |
|---|---|---|---|
| **> 0** | temporary invincibility | **time** — tick `0x80048654`, 1 per 2 frames | B06 |
| **< 0** | bubble shield (hit quota) | **hits** — absorb `0x8004A808`, +1 per hit | B08 |
| **= 0** | none | — | — |
| **= 1** | transient, written by the grain harvester while equipped | see [[SYS_grain_harvester]] | C13 |

The tick's `blez` guard at `0x80048648` is the linchpin: it skips non-positive
values, so a bubble is **time-invariant**, and an expiring invincibility **lands
exactly on 0** rather than underflowing into a bubble.

## The flags word is a different mechanism — and not this one

`0x800A6590` sits next to the slot and has repeatedly been confused with it. Decoding the
`ori`/`andi` immediate at all **26** of its writers gives the real map:

| bit | meaning | set by |
|---|---|---|
| `0x01` | ground/locomotion state | `0x8001D5F8`, `0x800485D0`, `0x80048634` |
| `0x02` | **transient** ~2-frame per-action flag — *not a power* | `0x8004A7B0` (damage), `0x8004B02C`, `0x8005D088`; cleared `0x80048588`/`0x80048600` |
| `0x04` | transient contact/AI flag | `0x8004A8E0`, `0x8004EB6C`, `0x8004FA1C` |
| `0x08` | **checkpoint marker** | `checkpoint_save` `0x80054E90` |
| `0x20` | **super jump (B09)** | `0x800588F8` in contact_pickup_walker, with sfx 75 |
| `0x80` | **grain harvester (C13)** | `0x80051EB0` |

Two consequences worth keeping:

- **Invincibility and the bubble use the slot, not a bit.** Some blue-lane powers *do* use
  flag bits — super jump is one — which is exactly why the older notes assigned B06 a bit.
  They were right that the mechanism exists and wrong about which tier uses it.
- **Reset semantics differ.** Respawn zeroes the slot outright (`0x8005B268`) but does
  `andi 0x0020` on the flags word (`0x8005B340`), i.e. **keeps only super jump**. So B09
  survives a respawn while B06/B08 do not.

No writer of `0x800A6590` exists anywhere in `0x8005C000–0x8005D000`, so the blue-plant type
handlers never touch it: they spawn a contact object, and *collecting it* grants the power.

### B09 velocity mechanism — 2026-08-02, first typed-state binding

Full evidence: `analysis/phase4_b09_super_jump_velocity.json`. Answers the row's own
`missing: Multiplier/state/timer` question for the multiplier specifically (not the timer
— B09 has no timer, per the reset note above: it survives respawn rather than expiring).
Isolated DuckStation session; the fixture (`movies/Phase4/A13/blue_seed_levels.movie.json`)
predates the 2026-08-01 Interpreter-safety finding and carries no CPU-mode metadata, so
handled as **poll-only** (no `accessLog`/`execTrace`/breakpoints armed at any point) —
safe under either execution mode.

**Static, exact-bytes finding**, at the very entry of `FUNC_80048138`
(`player_vertical_update`, already Canon-bound for `A03_jump`):

```
0x80048184  lhu $v0,144($s1)       ; offset 0x90 == 0x800A6590-0x800A6500
0x8004818c  andi $v0,$v0,0x20      ; isolate bit 0x20
0x80048190  beq $v0,$zero,+2
0x80048194  addiu $s3,$zero,-3072  ; NORMAL
0x80048198  addiu $s3,$zero,-3776  ; SUPER JUMP
```

`s3` is later copied to `s4` at the X-release jump-launch site (`0x80048BD8`, alongside
the `AIR_STATE=2` transition already documented in `src_re/player_update_80048138.c` —
the jump impulse integrates on **X release**, not press, matching that file's existing
state-machine description), then transformed: `s4 = round_half_away_from_zero((s4+384)/2)
- 256`, gated on `GROUNDED` (`lh v0,130($s1)`, offset `0x82` — the SAME field
`player_update_80048138.c` already independently names `GROUNDED`), and stored at
`0x80048D8C` (`sw $s4,48($s1)`) — offset `0x30`, which that same file independently binds
as `velocity_y`.

⚠️ **Corrected same day, later drill-down pass**: an earlier version of this section
stopped tracing at the `-256` step and reported **-1600/-1952** as final. That was
INCOMPLETE — one more gate follows at `0x80048D70` (the `GROUNDED` check): if
`GROUNDED != 0` the code skips straight to the store with `s4` unchanged (that IS
-1600/-1952, but is dead code for a real takeoff, since `GROUNDED` is cleared on the
X-press that starts the jump — same source). If `GROUNDED == 0`, the actual takeoff case,
it adds `+256` and clamps against `4097` before storing. **Computed with a mechanical
Python simulator of the exact branch structure (not another hand-trace, to avoid
repeating the same class of error twice): normal → -1344, super jump → -1696** (ratio
1.262). Both still negative — the corrected values don't change the sign-convention
cross-check's conclusion, only the exact magnitude.

**Sign cross-check against already-existing, independently-derived Canon**:
`player_update_80048138.c` states `velocity_y` is `<0 rising, >=0 falling/grounded` — both
computed outputs are negative, i.e. correctly signed for a rising takeoff. This
self-consistency across two independently-derived sources is real corroborating evidence.

**Live confirmation NOT achieved this pass** — flagged honestly, not glossed over. Two
sampling windows in the fixture were attempted; re-examined against the correct sign
convention, the "window A" event was almost certainly a **fall**, not a jump takeoff (Y
increasing = moving down, `velocity_y` positive = falling/grounded — the opposite
signature), and the super-jump-active window showed a small hop into what looks like a
pit, not a clean isolated jump press. **Three self-caught errors along the way, all fixed
before banking**: first read offset `0x2C` expecting `velocity_y` (it's `velocity_x` per
`config/record_types.yaml`; `velocity_y` is `0x30`) — caught by re-reading the config file
directly rather than trusting a paraphrased memory of it; then, after correcting the
offset, initially read a `+253` spike as a real jump takeoff without checking the sign
convention — caught by reading `FUNC_80048138`'s own pre-existing Canon note; then the
`-1600`/`-1952` figures themselves turned out incomplete, caught on a deliberate second
drill-down pass rather than left standing.

**Live confirmation attempted again, more rigorously, still not achieved — a property of
the fixture, not a fixable technique gap.** Rather than inferring jump windows from noisy
physics data, extracted all 20 X-release events directly from the movie's own recorded
input stream, filtered by press duration and co-held buttons, and sampled
`GROUNDED`/`AIR_STATE`/`velocity_y` around the cleanest-looking candidates on both sides
of the super-jump window. **Every candidate checked showed `AIR_STATE` already `1`
(airborne) for multiple frames *before* the recorded release** — these are mid-air button
taps during an already-falling sequence, not fresh grounded-stand launches; one candidate
sits inside a 160+-frame stretch where `GROUNDED=0` continuously. `movies/Phase4/A13/
blue_seed_levels.movie.json` traverses canyon-like terrain with frequent drops and does
not appear to contain an isolated standing jump in the regions checked. **Incidental
finding, not claimed as connected to the transform's own `-256` offset**: freefall
`velocity_y` increases by exactly `+256` per tick, a clean, confirmable gravity constant.
Clean live confirmation now needs either a purpose-recorded fixture (Flik standing still,
single X tap, with and without the power) or a different existing fixture — not a retry
of this one with the same method.

### Live confirmation ACHIEVED — 2026-08-02, same day, follow-up

The operator correctly pushed back that "needs a purpose-built recording" was vague and
not actually specified. Specifying it precisely made it obvious a **recording wasn't
needed at all** — a controlled experiment was: `level02.sav` (and `level03/04/05.sav`)
all load with Flik already `GROUNDED=257` (`0x0101`, matching the documented value
exactly) and `velocity_y=0`. Poked the power-flags bit directly (legitimate here — this
tests the *consequence* of the bit, not the already-solved *grant* mechanism), drove an
isolated X tap via `emulator.pressButton`, sampled `velocity_y` frame by frame after
release, once per condition.

**Raw data** (`velocity_y` per step after release):
```
normal:  -1216, -960, -704, -448, -192,  64, 320, 576, 832,1088,1344,1600
super:   -1568,-1312,-1056,-800, -544,-288, -32,224, 480, 736, 992,1248
```

Gravity confirmed live at exactly `+256`/step in both traces — matching the earlier
incidental freefall finding, now reproduced in a controlled, isolated jump. The
**difference between the two traces is exactly `-352` at every single step** (gravity
affects both equally and cancels out of the difference) — and the static derivation's
predicted difference is `-1696 - (-1344) = -352`. **Exact match.** Solving for how many
gravity ticks elapsed before the first sample gives exactly `0.5` independently for
*both* traces — one consistent half-tick sampling offset (the same frame-duplication
granularity observed earlier in movie playback) explains both, not two unrelated
discrepancies.

**Verdict: live confirmation achieved.** B09's velocity mechanism is now fully typed
*and* live-confirmed — not merely statically derived. Full data:
`analysis/phase4_b09_super_jump_velocity.json` §`LIVE_CONFIRMATION_ACHIEVED_2026-08-02d`.

## Observed site census — a LOWER BOUND, not a completeness claim

Rebuilt 2026-08-01 with `tools/census_address.py`, a may-constant value analysis with
interprocedural argument propagation, regenerated and checked by
`tools/phase4_b06_b08_census_gate.sh`. It resolves the aliased forms an immediate scan
cannot see — `sh v0,0x0(fp)`, `lh v0,0x0(a0)`, and crucially `sh v0,0x7e(s1)` where `s1`
is the player pointer *passed in by the caller*.

Doing so corrected the hand-built census it replaced, which had claimed "7 writers, 5
readers": it had **missed** `0x80051EA0` (the harvester's equip-moment write) and
`0x800588B0` (the B06 grant's guard read), and for true health had claimed 4 writers
where there are 6.

### Overlays

Censused 2026-08-01 with `tools/census_overlays.py` over 21 pristine blobs (20 per-level
`LEVEL*.BIN` + `MEMORY.BIN`) — code that had never been scanned.

- **Zero** overlay accesses to the power slot, read or write. A real negative, not an
  absence of looking: the blobs contain 1–128 `lui rX, 0x800A` address formations each,
  so they do compute addresses in that page; none lands on the slot.
- **Three** overlay reads of true health, all consumers, no writers:
  `0x800B41D0` (LEVEL03, `6 - health`), `0x800B3DAC` (LEVEL08, `bgez` **death check**),
  `0x800B3D50` (LEVEL10, `80 - health*20` → overlay var `0x800B41B8`, gated on player Z).

### Runtime writer union — the empirical half

Replaying every traceable fixture with a write watch, and running past movie end so a
transition/spawn `memset` is included:

| fixture | slot writes | writer PCs |
|---|---|---|
| B06 cold boot | 403 | tick, B06 grant, **BIOS memset** |
| B08 cold boot | 6 | absorb, B08 grant, **BIOS memset** |
| level transition | 401 | tick, B06 grant, **BIOS memset** |

**Zero writers outside the enumerated set.** Note `0xBFC02BB0` appears in *all three* — the
spawn `memset` is not an edge case, it fires on every level load. This cannot prove
absence: a writer on an unexercised path stays invisible.

⚠️ **Residual, enumerated rather than hidden.** Two independent gaps:

1. **The residual.** Accesses whose base pointer is loaded from memory rather than
   computed in the instruction stream are not resolvable. An earlier revision called
   this residual "demonstrably non-empty" for the slot because `0x8004AFB0` sits in
   that analysis class; that was wrong, because the site targets player+`0x82`.
   The census still enumerates unresolved-base accesses (including 75–1848 per
   overlay), so a negative closure claim is unavailable without resolving them.
2. **Writes performed by a CALLEE** — a class no store-site census can see, now
   **enumerated** by `tools/census_callee_writes.py`. The transition clear at
   `0xBFC02BB0` is a generic BIOS `memset(dst, val, len)`; a census over the BIOS finds
   zero hits and zero `lui 0x800A` material in all 512 KB, because the BIOS never forms
   the address — it receives it.

   A `jal` scan misses it too: the game reaches the BIOS through a PsyQ stub
   `0x8005F7AC` = `addiu t2,0xA0 / jr t2 / addiu t1,0x2B`, which is **register-indirect**
   (scanning for `jal 0x000000A0` / `0x800000A0` returns **zero** resident sites). The
   *thunk* is called by ordinary `jal`, so its **26** call sites are enumerable. An early
   fixed-point pass resolved 24 and left two register arguments open. That "two open"
   result was stale first-round state: the converged static pass resolves both.

   Watching the BIOS store PC with
   `capture=[ra,a0,a2]` and filtering for `a0 == 0x800A657E` gives `ra = 0x80046B70` →
   **`0x80046B68` in `level_load_player_spawn_writer`: `memset(player_block, 0, 168)` on
   spawn.** That runtime observation establishes the transition clear. Independently,
   static propagation resolves `0x80046B68` to `(0x800A6500,168)` and the formerly
   "still unattributed" `0x8004DC40` to `(0x80095358,48)`, which is disjoint from the
   power slot.

**Correction history.** This table previously claimed eight writers by adding
`0x8004AFB0` as a runtime-only knockdown clear. That was wrong: the pristine
instruction pair at `0x8004AC70` and `0x8004AFB0` makes the store effective
address player+`0x82`, not this slot at player+`0x7E`.

**7 statically resolved direct resident writers:**

| PC | function | action |
|---|---|---|
| `0x800588D0` | contact_pickup_walker | B06 grant `:= 400`, **unconditional** |
| `0x800589A8` | contact_pickup_walker | B08 grant `:= -3`, **unconditional** |
| `0x80048654` | player_vertical_update | tick: `v > 0 -> v - 1` |
| `0x8004A808` | damage handler | absorb: `v < 0 -> v + 1` |
| `0x80051F60` | harvester_equip_and_active_update | `:= 1` while flag bit `0x0080` set |
| `0x8005B268` | respawn_transition_state_handler | `:= 0` (bulk player-block zero) |
| `0x80051EA0` | harvester_equip_and_active_update | `:= 1` at the **equip moment**, paired with `ori 0x0080` into the flags word two instructions later |

Separately, the callee-performed transition clear is attributed to the
`memset(player_block, 0, 168)` call at `0x80046B68`; the executing stores are in
the BIOS and are not an eighth resident store instruction.

**7 readers:** `0x80048640` (tick read), `0x80049718` (call-site gate — skips the
damage call entirely when the slot is non-zero), `0x8004A7A4` and `0x8004A7E0`
(handler), `0x80051C3C` (the **BUBBLE's** renderer — `bgez` at `0x80051C44` skips it unless the slot
is **negative**), `0x80055BC4` (the **positive/invincibility** path — `blez` skips unless
the slot is > 0 — then effect 57, requiring the harvester bit **clear**), `0x800588B0`
(the B06 grant's `bgtz` guard read).

No claim is made that nothing else touches this slot — see the warning above.

## Capacity, lifecycle, transition, reset

- **Capacity** — both grants are *unconditional stores*, so each is a clamped
  **refresh**, never additive. B06's `bgtz` guard at `0x800588B8` only suppresses the
  pickup sound when already active. Confirmed at runtime: poking `-1` immediately
  before the natural bubble grant yields `-3`, not `-4`.
- **Lifecycle end** — B06 ticks to exactly 0 and vulnerability returns; B08 pops at 0
  and the next hit lands.
- **Transition** — the shared slot is **last-write-wins across powers**: collecting a
  bubble while invincible overwrites `400` with `-3` and discards the invincibility.
- **Reset** — `:= 0` on respawn (`0x8005B268`; a `sh zero` with no data dependence on
  the prior value, so it resets *any* power state). The earlier addition "and on
  the knockdown reaction" was wrong; that store targets player+`0x82`.

## Damage immunity is complete, and it is register `s1`

All damage funnels through the handler at `0x8004A700` — **6 callers**, enumerated
statically. Inside it, `0x8004A7B4 bne slot,zero` **routes** to the interception
block; what actually suppresses the health write is register **`s1` being cleared**
(`0x8004A818` / `0x8004A800`) and tested by `0x8004A828 beq s1,zero`. A non-negative
slot at `0x8004A7E8` does **not** fall through to damage — it lands on `0x8004A80C`,
which also clears `s1`.

The suppressed write is `0x8004A888 sh v1,0x6594(at)`. **6** instructions in the resident image write `0x800A6594`, and `0x8004A888` is the
only one that *decrements* on a contact path. Verified by inspecting all five others:
`0x80046C04` spawn init, `0x80055124` sfx glue, `0x80058890` **heal pickup**
(`health += 1`, sfx 62), `0x8005291C` results-screen clamp to 4, `0x8005B30C` respawn
restore. So intercepting `0x8004A888` is the whole of contact-damage immunity — the
claim holds, but the earlier count of "exactly 4" that supported it was wrong.

## The harvester intersection is not what it looks like

`0x80051F60` writes **1** into this slot whenever power-flags bit `0x0080` is set, and
a positive slot is what the damage path treats as invincibility. **That is not the
mechanism.** `execTrace` over the handler and all six of its call sites:

| arm | handler entries | health |
|---|---|---|
| no harvester | **3** (all from `0x8004B4A0`), all reaching the health write | 4 → 1 |
| harvester | **0**, from any call site | 4 |

The handler is never entered, so the interception plays no part. The cause is
`0x8004B160 andi v0,0x80` → `0x8004B164 bne` in `actor_player_contact_resolver`,
which branches past its damage call. Immunity while harvesting comes from the **flags
word**, not this slot. Corroborated by the game itself: `0x80055BC4` requires slot > 0
**and** harvester bit **clear** before the invincibility effect.

## Code identity across scenes — NOT campaign breadth

16 distinct scene ids (1–15 and 17). In each, all 16 bound instruction words read
**live** are byte-identical to the pristine EXE, and `+400` ticks while `-3` is
untouched. Zero mismatches.

⚠️ This establishes *code identity*, which is not by itself campaign breadth. Breadth is
carried separately, below.

## Campaign breadth

Both powers have now been collected **naturally** across **three disc directories** — the
directory matters because it selects the overlay pair:

| stage | disc dir | collected |
|---|---|---|
| level 1 | `LEVEL01/LEVEL.DAT` | B06 |
| level 6 | `LEVEL01/LEVEL1.DAT` | B08 |
| **level 13** | **`LEVEL09/LEVEL.DAT`** | **both**, full lifecycles — 400-tick countdown and a three-absorb pop |

Applicability across the campaign is *enumerated*, not sampled: from the per-level plant
model table `*(0x800A649C + type*4)`, **B06 is producible in 10 of 15 stages and B08 in
11** (`tools/enumerate_applicable_levels.py`). Corroborated independently — the one
gameplay VAB bank that stubs the invincibility collect sound is scene 3, exactly where
that table reports B06 non-producible.

The remaining stages are covered by **measured** code identity plus **measured**
availability rather than by observation. That is an argument, and is labelled as one.

## Visual

Phase-matched `gpu.captureFrameSnapshot` / `gpu.diffCurrentFrame` (same state, same
frame count — required, because the flash is animated): control vs control **0**
changed pixels of 488,000; timer on vs control **4,054** changed pixels in a single
151×327 box on the player.

## Production chain — how a power comes to exist

Closed end-to-end, every hop derived from the pristine EXE:

```
blue token (type-0x3f kind 0x2A, obj 0x17) -> counter 0x800A6599  [persists across levels]
  -> butt-slam a seed -> FUNC_8005BDBC: idx = color*4 + (count-1)
  -> pair table 0x8007A448[idx] -> (type, extra)
  -> plant slot 0x80090BF0 + n*0x30, jr table 0x8001B848[type-2]
  -> the type handler calls contact_alloc 0x80059E44, ctor in a3
  -> metaB 0x8007941C[ctor] -> +0x00 = ACTION ID
  -> walker dispatch 0x8001B570[action-2] -> the grant
```

| blue | table entry | ctor | action | handler | effect |
|---|---|---|---|---|---|
| ×1 | type 7, extra `0x2000` | **`0x25`** | `0x0C` | `0x800588B0` | **B06 invincibility := 400** |
| ×2 | type 7, extra `0x3000` | `0x26` | `0x09` | `0x80058864` | B07 health |
| ×3 | type 6, extra `0x0000` | **`0x1F`** | `0x2E` | `0x80058998` | **B08 bubble := −3** |
| ×4 | type 7, extra `0x4000` | `0x27` | `0x0F` | `0x800588D4` | B09 super jump |

The invincibility ctor was ambiguous among four candidates; it is **`0x25`**, from the
handler's own arithmetic `(extra >> 12) + 0x23` at `0x8005C7D8`–`0x8005C7E0`. The bubble's
is `(extra >> 12) + 0x1F` = `0x1F`.

The ×4 row is a useful cross-check: it says tier 4 is **super jump**, independently
confirming the flags-bit map above — super jump is the one blue power that uses a
`0x800A6590` bit rather than the slot.

**Asset dependency:** the plant *body model* comes from `*(0x800A649C + type*4)`, a
per-level table filled at load — **NULL ⇒ the plant works but is invisible**. So B06 needs
`PLANTS/PLANT07.ALL` and B08 needs `PLANTS/PLANT06.ALL`.

## Render and asset binding

**The pickups are screen-aligned sprites**, drawn by `FUNC_80014844`
`contact_record_billboard_render` (sole caller `0x800225B0`), which walks the 64-record
contact array at `0x800B0D18` (stride `0x38`) and emits one `POLY_FT4` each. The GTE
rotation matrix is loaded **once outside the loop** to a constant `diag(1.6, 1.0, 1.0)`
and only the translation is per-object, so the quad never rotates with the camera.

⚠️ **Correction to an earlier reading.** These are contact objects, not type-0x3f
entries, and I recorded that the `0x80096B98` kind→descriptor Canon therefore did *not*
cover them. **It does.** The contact renderer uses the same table and the same descriptor
structs — only the *index* differs:

```
0x8001496C  lhu t2, 0x20(t8)      ; rec+0x20 = the metaB ACTION ID
0x80014978  sll t2, t2, 2
0x8001497C  add t2, t2, t7        ; t7 = 0x80096B98
0x80014980  lw  t2, 0(t2)         ; -> the descriptor
```

So `rec+0x20` is **double-duty**: it selects both the behaviour handler
(`0x8001B570[action-2]`) and the sprite descriptor (`0x80096B98[action]`). Action `0x0C`
is simultaneously B06's grant handler *and* its sprite; `0x2E` likewise for B08.

**Spawn kinematics** come from table A `0x80079E30`, indexed by the stack argument
(stride `0x14`), each row `{selector_pack; v0..v3}` whose four nibbles pick a transform
applied by `fcn.800593E8` into `rec+0x0C/+0x10/+0x14/+0x18`. Row 3 (B08) is all zeros —
nibble 0 is the *pass-through* case, so that is the "spawn perfectly still" profile, not
a missing row as an earlier note guessed. Row 6 (B06) gives symmetric XZ scatter plus an
upward impulse. `fcn.800593E8` draws its randomness from a byte cursor at `0x800822F4`
that points **into the EXE text** — the game uses its own image as a noise table.

**Per-level asset dependency: none** beyond the plant body models. `0x80096B98` is BSS;
the descriptor pointers for `[0x0C]` and `[0x2E]` are identical across LEVEL01/04/06/08/13,
the sprite pixel bytes and palettes are **byte-identical** across all five, and only
descriptor `+0x04` (tpage) and `+0x06` (clut) are runtime-written. Only the VRAM page and
CLUT row shift per level.

*Residual:* who writes that rebinding at level load is unattributed — a **pre-existing
Phase-3 gap** (`phase3_render_descriptors.json` records `writer_attribution: unresolved`),
not one this campaign introduced.

## Cold-boot oracle (DoD item 1 — met)

Two operator-recorded **from-boot** movies, replayed at 60 Hz on Interpreter and
asserted by `tools/phase4_b06_b08_oracle.py`, which computes its artifact and exits
non-zero on any failed check. **No pokes anywhere in either run** — this is the whole
point, because a poked timer proves the damage path *reads* the slot, not that
collecting the pickup *produces* that state.

**B06** — `movies/Phase4/b06_invincibility_hits_from_boot.movie.json`, **LEVEL01
(scene 1)**, 6522 frames, **5/5**:

| check | result |
|---|---|
| natural grant | `0x800588D0` wrote 400 at frame 5336 |
| protected | 16 intercepted contacts while active, **0** writes to true health |
| tick | 400 tick writes, strictly −1 each |
| expiry | lands **exactly on 0** at frame 6154 — never negative, which would silently become a bubble |
| vulnerable after | 2 damage writes at `0x8004A888` |

**B08** — `movies/Phase4/B08_bubble_repeated_hits_from_boot.movie.json`, **LEVEL06
(scene 11)**, 6959 frames, **6/6**:

| check | result |
|---|---|
| natural grant | `0x800589A8` wrote −3 at frame 6046 |
| absorbs | −2, −1, 0 |
| no damage while shielded | **0** health writes between grant and pop |
| **not time-consumed** | **0** tick writes while the quota was negative |
| pop | quota reached 0 at frame 6554 |
| vulnerable after | 3 damage writes at `0x8004A888` |

The time-invariance row is the one that could not be obtained any other way: that a
bubble is hit-consumed and *never* time-consumed is now observed in a natural
playthrough rather than inferred from the `blez` guard or produced by a poke.

B06's fixture is also the first natural collection of either pickup **outside scene
11**, which is what makes the breadth item advanced rather than a hard fail.

Fixtures are hash-pinned in `analysis/phase4_b06_b08_fixtures.json` (including the
`.sav` hash the movie format omits); artifacts are
`analysis/phase4_b06_oracle.json` and `analysis/phase4_b08_oracle.json`.

## Lifecycle at boundaries

Probed by `tools/phase4_b06_b08_lifecycle.py` (artifact
`analysis/phase4_b06_b08_lifecycle.json`).

- **Pause freezes the timer.** 15 ticks in 30 running frames → **0 ticks in 180 frames
  while paused** → 16 ticks in 30 frames after resume. An invincibility does not drain
  while the player sits in the menu, because the tick is driven by the player update and
  the pause stops it.
- **The bubble has a visual: a shell colour ramp sized to its quota.** `0x80051C3C` reads
  the slot, `0x80051C44 bgez` runs the body only for a **negative** slot, and
  `0x80051C48/4C` compute `slot*3` to index **backward** from `0x80078E55`:

  | slot | address | RGB |
  |---|---|---|
  | −1 | `0x80078E52` | `40 40 40` |
  | −2 | `0x80078E4F` | `60 60 60` |
  | −3 | `0x80078E4C` | `80 80 80` |
  | −4 | `0x80078E49` | `00 00 00` |

  The shell **brightens with hits remaining**, and the table is sized *exactly* to the
  3-hit quota — slots −1..−3 ramp and −4 falls off to black. An independent corroboration
  of "capacity 3, clamped refresh", from the renderer rather than from the grant.

  ⚠️ **Correction.** An earlier revision of this note attributed **B06's** frame-diff
  result to `0x80051C3C`. That was wrong — it is the bubble's renderer. The frame-diff
  *observation* stands (4,054 changed pixels, 0-pixel control); only the mechanism was
  misattributed. B06's visual path is `0x80055BC4`.

- **Audio: a one-shot collect sound, and nothing ongoing.** Two independent layers.
  *Dispatch* — on the cold-boot movie the grant block executes once and calls
  `sfx_dispatch(65)` once; with the slot preset positive, that call executes **zero**
  times while the store **still writes 400**, so the `bgtz` at `0x800588B8` suppresses
  only the sound (and re-confirms the grant is a clamped refresh).
  *Actual audio* — an SPU trace shows **two key-ons** one frame after a natural grant
  (voices 1 and 2) versus **one** when already active: exactly one voice is suppressed.
  So a real voice starts, not merely a function call.
  *Which sample* — resolved via [[SYS_sfx_system]] and `analysis/sfx_id_vag_map.json`:
  id 65 → prog 0, tone 49, **VAG 50** of the active **per-level** bank (not GLOBAL, which
  holds only 43 tones / ids 16–58). That is a **0.842 s one-shot**, and it is
  **byte-identical across all 14 gameplay banks** — one sound duplicated per level, not a
  per-level variant. Six banks carry a 2 ms stub there instead: five `…C` banks plus
  `LEVEL03_LEVEL1B`, which is scene 2's gameplay bank.
  ⚠️ There is **no sustained audio** while a power is active — the only sound is that
  one-shot collect effect, which is what the operator observed.
- **Powers are never persisted by the game.** No save or checkpoint routine writes
  `0x800A657E` at all. `checkpoint_save` (`0x80054E5C`–`0x80054E90`) writes position
  `0x6550`/`0x6554`/`0x6558`, `0x6578`, and the power-**flags** word `0x6590` with
  `ori 8` — but never the slot. So an active power cannot survive a checkpoint restore,
  and the flags word and the slot have *different* persistence. (An emulator save-state
  round trip does restore it, which only shows it is plain RAM.)
- **A power does NOT survive a level transition — and a BIOS routine is what clears it.**
  With the slot at 20000 before the ending area is entered (gameplay demonstrably live:
  the tick ran 68 times), the exit is crossed, and at frame 113750 **`0xBFC02BB0` writes
  0 twice**. That address is **BIOS ROM**, a kernel memory-clear during the level load —
  *not* the game's respawn handler `0x8005B268`, which does not fire on this path.
  Fixture: `movies/B06_LevelTransition.movie.json`, which **requires the arm-phase tag**
  (`tools/rephase_movie.py --tag-arm-phase`) — untagged it desyncs and never reaches the
  exit. The post-level results screens must be driven with injected input, because the
  movie's input stops at its last frame.

## Source closure

`src_re/player_power_slot_800a657e.c` — documentation-grade reconstruction of the slot's
behaviour (all 7 statically resolved direct writers, all 7 resolved readers, the 6 handler
callers, the callee-class clear, the production chain), explicitly *not a build unit*.
The former "all eight writers" source-closure count was the same false knockdown-site
inclusion corrected above. Guarded by
`tests/test_phase4_b06_b08_power_slot.py`, 77 assertions.

The DoD's *"remaining byte/layout mismatches are explicitly bounded"* is satisfied at
**zero** — every function touching the slot is byte-matched hand-written assembly passing
the SHA-1 build gate. ⚠️ But `asm/hand_written/` is **gitignored**, so that claim must cite
`tools/repro_inputs.sha256` + `verify_repro_inputs.py --provision`, never the working tree.

## Verification status

Gates: `phase4_b06_b08_census_gate.sh` (store sites + callee writes + overlays + runtime
union), `phase4_b06_b08_oracle.py --row b06|b08`, `phase4_b06_b08_pin_fixtures.py`,
`check_b06_b08_surfaces.py`, `validate_vault.py --check`.

A **clean-clone run** verifies the surface check, the test suite and the fixture manifest.
The census gate cannot run there — it needs the pristine EXE and staged blobs, both
gitignored as copyrighted. That is a property of the repo, not a gap in this subsystem.

## Not established

- **The frontier is not complete** (DoD 2). The alias-aware census resolves far more
  than the immediate scan it replaced, but it still reports accesses through bases it
  cannot resolve. An earlier revision called that residual "demonstrably real" for this
  slot because `0x8004AFB0` sat in it. That evidence was wrong: the site is a real
  unresolved-base access, but not an access to this slot. The unresolved set still
  prevents a whole-image negative claim; it does not itself prove another slot access.
- ⚠️ **`0x8004AFB0` IS NOT A WRITER OF THIS SLOT.** Two separate claims here were wrong
  and both are retracted (2026-08-01). This note first said the block "never executes in
  the fixture corpus" — it does, at frame 5966. It then said the block clears the power
  slot — it does not: `fp = v1 + 4` (`0x8004AC70`), so `sh zero, 0x7e(fp)` lands on
  **player+0x82**, four bytes past the slot. Measured `fp = 0x800A6504`, and a live
  400-tick invincibility ticked straight through the clear untouched. Full account:
  [[#The knockdown site — not part of this subsystem]] below.
- ~~Audio~~ — **closed for both rows.** A caller census
  (`tools/census_sfx_callers.py`) resolves the id at 20/22 `sfx_dispatch` and 90/92
  `play_sound` sites, and settles the question the id alone could not: **`65` has exactly
  one call site**, so invincibility's sound is its own, while **`-3` has four** — three in
  the generic type-0x3f pickup handler — so **the bubble plays the generic collectible
  sound and has none of its own.** Runtime ablation confirms the dispatch is what makes
  the sound: NOPping the single `jal` at `0x80058998` removes exactly two voices (1 and 6)
  at the grant frame. The shared contact sfx 14 is bound to its one site `0x8004A820`.
- ~~No semantic source~~ — **closed** (DoD 8). `src_re/player_power_slot_800a657e.c` is
  documentation-grade C covering the whole subsystem, guarded by 77 assertions in
  `tests/test_phase4_b06_b08_power_slot.py`.
- ~~Breadth~~ — **closed** (DoD 6). Invincibility is collected naturally in LEVEL01 and
  the bubble in LEVEL06/scene 11 plus a second stage, so the single-stage confinement is
  broken for both rows. The remaining stages are argued from measured resident-code
  identity and availability tables rather than collected individually, and that argument
  is labelled as such — collecting in ten more stages would only watch identical code
  execute.
- **The render/asset boundary is not closed** (DoD 5). The runtime writer that rebinds
  descriptor `+0x04`/`+0x06` (tpage/clut) is unattributed. It is inherited from Phase 3,
  which explains where it came from but does not exempt it, because it intersects these
  powers' visual contract and any future asset mod.
- **The evidence wrapper is below standard** (DoD 9). The oracle runner retains no
  mounted-media identity, no debugger binary/capability provenance and no watch
  saturation/truncation status, all required by `engineering-specs/phase4-closure.md`;
  the oracle artifacts predate the current generator shape; and there is no repo-wide
  Phase-4 campaign inventory, fixture audit, evidence DAG or whole-phase gate.


Superseded and no longer true, kept here because they were stated as limitations in
earlier revisions of this note: there *is* now a deterministic cold-boot oracle for
both rows, the fixtures *are* centrally hash-pinned, and committed runners *do*
regenerate and falsify the frontier and lifecycle claims.

## STOP DECISION (2026-08-01) — rows stay partial, frontier state is `open`

Work on B06/B08 is **stopped**. Not because the mechanism is unclear — it is thoroughly
understood — but because the remaining DoD items need general capabilities this campaign
should not build in isolation. Revisit only when general pointer typing or asset-loader
work naturally resolves the remaining classes.

### Two rules that must not be conflated

I proposed amending the closure policy so item 2 could be met by "named residual +
runtime falsification." **That was rejected, correctly, and no amendment is needed** —
the policy already distinguishes:

| rule | source | who applies it |
|---|---|---|
| a frontier is `closed` only when the **unresolved-intersection set is empty** | [[Phase 4 - Acceleration Tooling Strategy]] | the **compiler**, automatically |
| a **bounded unknown may remain** if explicit, evidence-backed, with a named next experiment, and not invalidating the conclusion or the **future-MOD consumption contract** | `engineering-specs/phase4-closure.md` | a **reviewer**, with judgement |

The compiler is *deliberately* forbidden from exercising the judgement that awards the
second. That is the design, not a gap.

### Three frontier states

1. **`closed`** — unresolved-intersection set empty. Machine-emittable.
2. **`reviewed_bounded`** — a residual remains, but each *class* is semantically bounded
   and proven not to invalidate the stated behaviour or the supported MOD operations.
   **Awarded by a reviewer with a written consumption contract — never by automation.**
3. **`open`** — unresolved paths may still affect the subsystem. Machine-emittable.

**B06/B08 are `open`.** Reducing 416 → 251 and observing no runtime hits is real progress
and is **not a proof**. It does not earn `reviewed_bounded`.

⚠️ **Runtime absence is not proof of absence.** A replay cannot show that an *unexecuted*
pointer path never reaches the slot. This note states that plainly because I violated it
myself: having written exactly this earlier the same day, I then proposed runtime
falsification as a closure criterion. That is the reasoning error that caused the
original false closure, and it must not be reintroduced under a new name.

### What is safe to build on today

**Gameplay mechanism only** — sufficiently understood for **duration, quota, sound, grant
and placement** mods: the sign-multiplexed slot; B06 = 400 ticks at 1 per 2 frames
(~13 s); B08 = −3 hits; grants unconditional (refresh, never additive); the `blez` guard
making expiry land exactly on 0 and never ticking a bubble; respawn and level-load
clears; sfx 65 unique to B06, −3 the generic collectible sound.

**Explicitly NOT claimed:** the complete subsystem frontier and the visual/asset-loading
contract. Do **not** build an asset or re-skin mod on the descriptor path — item 5's
tpage/clut rebinding writer is unattributed — and do **not** assume the exceptional-path
list is complete (item 4).

### Why amending item 2 would not have helped anyway

Items **4, 5 and 9 are all still ADVANCED**. Even with item 2 relaxed, these rows would
not close. The proposal rested on a false premise as well as an unsound criterion.

## Static frontier: what is now PROVEN, and what is still only counted

Three results from the 2026-08-01 data-flow pass. The first two are sound exclusions;
the third removes a residual that turned out to be a tooling artifact.

### `$gp` is a compile-time constant — a sound exclusion of 916 accesses

`gp == 0x80081D98`, established from the image alone rather than assumed:

- exactly **one** materialization — `lui gp,0x8008 / addiu gp,gp,0x1d98` in `stup1` at
  `0x8005F710`;
- the only two other writes to `$gp` in code are `lw gp, 0x68(sp)` **epilogue restores**
  (`gte_rtps_mesh_assembler` `0x80018800`, `decompress_lz_bitstream` `0x8001A8E4`), each
  matched by an `sw gp, 0x68(sp)` **prologue save at the same stack slot** — they restore
  the saved value, they do not redefine it;
- the remaining 30 apparent writes all lie in `data_nonzero`/`string` regions per
  `analysis/memory_map.json` — data being decoded as instructions.

So every one of the **916** gp-relative accesses in the resident image has an exactly
computable effective address, and **none lands inside the player block**
`0x800A6500..0x800A65A8`. Seeding it cut the same-width residual **937 → 882** and the
image-wide residual **31,342 → 29,396**.

### The straddling-store hole — real, and empty

The census hit-test was `if ea in targets`, which only catches an access that *starts* on
a target byte. The slot sits at offset `0x7E` and is therefore **not word-aligned**, so an
aligned `sw` at `0x800A657C` writes bytes `7C..7F` and clobbers the slot while starting
two bytes below it. That access was structurally invisible to every census before this.

The test is now an overlap of `[ea, ea+width)` against the target range. **Zero** such
accesses exist for this target, cross-checked two independent ways: the narrow 2-byte
census and a whole-player-block census return exactly the same 14 accesses, all width-2,
all starting exactly on the slot. Because the real image never exercises the new path, it
is unit-tested on a synthetic image instead — a straddling word store is caught, an exact
halfword store is still caught and not mislabelled, and an adjacent word store that stops
short is not a false positive.

### Callee destinations: 0 unresolved (was "1 unattributed")

All 26 call sites of the PsyQ `memset` thunk now resolve statically.

| site | function | resolved call | verdict |
|---|---|---|---|
| `0x80046B68` | `level_load_player_spawn_writer` | `memset(0x800A6500, 0, 168)` | **covers the slot** |
| `0x8004DC40` | `respawn_collision_reset` | `memset(0x80095358, 0, 48)` | **provably disjoint** |

`0x80046B68`'s single caller `0x8005BAA4` in `gameplay_state_reset_cursor_seed` passes
`a0 = 0x800A6500`; 168 bytes spans the whole player block. This was previously attributed
only by a runtime BIOS-store watch and is now static. `0x8004DC40`'s two call sites both
pass `a0 = 0x80095358` — the **camera** block — writing `0x80095358..0x80095388`, nowhere
near the slot.

The long-carried "one unattributed callee destination" was a **tooling artifact**:
`census_callee_writes.py` kept the *first* record per call site, which is fixed-point
round 0 — before interprocedural argument propagation runs, when entry arguments are still
the empty set. It was reporting a pre-convergence answer as an unresolved destination.

**What this does not close.** The same-width aliased accesses and indirect calls are
still *enumerated*, not semantically bounded, so DoD item 2 stays ADVANCED — see the two
sections immediately below for the corrected counts and the region-provenance result.

### The residual was inflated 2x by a counting bug — corrected: 882 → 416, 238 → 149

`census_address.py` deduplicated `hits` by PC before returning them (`seen.setdefault`)
but returned `unresolved` **raw**. A function's containing block gets reprocessed every
time an incoming edge's state changes while the worklist converges, and every revisit
re-ran the whole block — including re-appending the SAME unresolved instruction to the
list, once per revisit. The reported "882 same-width residual sites" and "238 indirect
calls" were never counts of distinct instructions; they were counts of *visits* to
instructions during convergence, a number with no stable meaning.

Deduplicating by PC (matching what `hits` already did) gives the true distinct-site
counts: **416** same-width residual accesses, **149** unresolved indirect calls. This
was real data with a real inflation baked in, not numbers invented from nothing — every
prior claim built on "roughly half of 882/238 are distinct sites" was quietly true, it
was just never measured or disclosed. `tools/census_address.py`, `tests/test_phase4_b06_b08_power_slot.py`, and this note are corrected; `src_re/player_power_slot_800a657e.c`
records the full arithmetic.

### Region provenance (`tools/region_provenance.c`) — 165 of 416 excluded, 251 open

> Running tally, each step cross-validated against the Python baseline: 35 (block-local
> `sll`+`addu`) → 63 (cross-block shift hints) → 72 (walking-pointer APs) → **165**
> (loop-carried merges fixed properly + a straddle-window soundness repair; see
> [[#Loop-carried merges, a soundness repair, and combined-prover accounting]] below).
> The intermediate numbers in the subsections that follow are that history, kept as
> the audit trail rather than rewritten.

Most of the 416-site residual isn't the player pointer with an unresolved *value* — it's
a **different, named object** (a dirt-pile record, a ground-height query record) reached
through array indexing that constant-propagation can't pin to one address, because the
index is data-dependent. The question that matters isn't "what's the exact address," it's
"can this base register's value family ever equal the target" — answerable even when the
exact value isn't, via alignment: the compiler emits `sll`+`addu` for `array[i]`, so if a
base is provably `K + i·S` for a fixed pool base K and stride S read directly off that
instruction pair, the target is unreachable whenever `(target − offset − K) mod S ≠ 0`,
for **every** possible i — no assumption about array size.

Built as a standalone C port of `census_address.py`'s value analysis (a from-scratch
second implementation, not a wrapper), extended with this REGION lattice value. Two
soundness tiers, both disclosed rather than blurred: **EXCLUDED_ALIGNMENT** is
unconditionally sound given the base genuinely is `K + i·S`; **EXCLUDED_NEGATIVE_INDEX**
additionally relies on the standard non-negative-array-index convention.

**Validated, not asserted.** `tools/phase4_region_provenance_report.py` runs both
implementations and reconciles them: the C tool's hit set matches Python's 14 exactly,
and `(C's remaining residual) ∪ (C's exclusions)` equals Python's 416-site baseline with
**zero lost sites and zero spurious ones** — the region analysis only ever *moves* a site
from residual to excluded, never invents or drops one. Result: **63 excluded** (57
alignment, 6 negative-index), **353 remain open**.

Two exclusions were hand-verified against the disassembly rather than trusted from the
aggregate count: one lands on `0x800A7E48`, the Canon-documented collision sector table
(base and even the field-offset arithmetic check out exactly), independently confirming
the technique against a structure this campaign already knows. Another, in
`ground_height_query`, initially looked like a possible bug — its detected stride (16)
undersells the register's TRUE index multiplier (48, from `v1·3` then `<<4`, which the
tool's peephole only partially sees) — but a smaller assumed stride is provably a
**superset** of the true reachable set, so the exclusion stays sound; it is only more
conservative than the finest possible analysis would be. Documented in the tool's header
rather than silently accepted.

**Extended to cross block boundaries (2026-08-01d).** The `sll`/`addu` shift-hint now
flows through the same worklist that already propagates register values — a flat 3-state
lattice (BOTTOM/unmerged, a concrete shift amount, or TOP/invalidated-or-conflicting),
merged exactly like register values. An index computed in one block and consumed by an
`addu` in a *later* block is now recovered, not just the single-block case: **35 → 63**
excluded, **416 → 353** residual. Re-validated with the same zero-lost/zero-spurious
guarantee. One new exclusion hand-verified (`0x80042108` in `vec_normalize_len_1ac4`,
`region_base 0x800A0000` stride 4 offset `-14220`: `40202 mod 4 = 2`, nonzero →
excluded) — its instruction span has no visible local branch, so the block split it
needed came from a distant branch *targeting* mid-range, exactly the case the earlier
block-local peephole structurally could not see. Still not fully general: a shift amount
only survives across blocks where nothing else touches that register, and disagreement
between merged paths collapses to TOP rather than being reconciled — reduced recall, not
unsoundness.

Resolved-jalr propagation and global-pointer provenance were deliberately not ported from
Python — both measured **zero** effect on this residual in the Python implementation, so
porting them bought nothing verifiable.

**Loop-bound extraction — TIER 3, `EXCLUDED_OUT_OF_BOUND` (2026-08-01e).** Alignment alone
(Tiers 1–2) can only ever say "not reachable at *this* residue" — an aligned,
non-negative index still looks reachable even when the array is provably too small or
positioned wrong to ever get there, because alignment never looks at the loop's own
bound. Tier 3 reads that bound straight out of the disassembly: the `slti`/`sltiu
idx,N` comparison that gates the loop is tracked the same way the `sll` shift is (a
`bound_hint` side-channel, propagated cross-block through the identical BOTTOM/known/TOP
lattice, and copied through the `sll` when the raw index gets shifted into a byte
offset). A site excludes under Tier 3 when the aligned, non-negative index the target
would require is `>= N`. Strictly stronger than Tiers 1–2 — it can close an access
whose residue class the target coincidentally lands on, which alignment structurally
cannot.

Weaker soundness than Tier 1, same class as Tier 2: it assumes the detected comparison
genuinely *gates* the index at the region's formation point, not merely that "some
comparison against this register happened somewhere" — disclosed in the tool's header,
not hidden.

**Hand-verified against real disassembly**, not trusted from the aggregate: whole-image,
Tier 3 finds 27 exclusions. In this row's 34-function scope it finds **zero** — a real,
disclosed negative result, not a failure. One whole-image example verified end to end:
`0x800370A4` in `collision_probe_candidate_pass`. `0x80036E98 slti v0,t3,48` /
`0x80036E9C beq v0,zero,0x800370C0` gates the *entire rest of the function* on `t3 < 48`;
`t3` then feeds `0x80037030 sll a0,t3,3` (stride 8, matching the tool's own detected
stride exactly), and that same `a0` forms the region read at the target instruction. The
tool computed `idx = 11315` against `idx_bound = 48` — both the bound and the stride the
tool reported match the disassembly precisely, not a coincidence of the aggregate count.

This is real, tested, reusable infrastructure for every future row's item-2 question —
`tools/region_provenance.c` takes any target address as a CLI argument — even though it
adds nothing to *this* row's number today.

**Walking-pointer regions — a second REGION source (2026-08-01f).** Scoping methodology
2 (type-provenance) surfaced something more immediately useful. `berry_projectile_update`
walks the contact array with `s0` set at entry (`lui s3,0x800b / addiu s3,s3,3352 /
addiu s0,s3,34` = `0x800B0D18 + 0x22`), then `addiu s0,s0,56` inside a loop — 56 = `0x38`,
the documented contact-record stride. `s0` starts as an exact compile-time constant, but
the value analysis's CONST-set union (capped at 6 distinct values) collapsed to TOP the
moment the loop exceeded that cap, discarding a perfectly regular arithmetic progression
that is exactly as region-representable as the `sll`+`addu` case.

Fixed the same way as the block-crossing extension: not by pattern-matching the `addiu`
instruction, but as a property of the value SET itself — in `merge_val`, when a
CONST-CONST union would exceed the cap, check whether the sorted values form a strict
arithmetic progression (every consecutive delta equal and non-zero); if so, convert to a
REGION instead of collapsing to TOP.

**One real soundness wrinkle, handled.** For the `sll`+`addu` case, `rbase` is a proven
compile-time literal — the array's true start. For a walking pointer, `rbase` is merely
the *smallest value this analysis happened to observe* — the true walk could extend
further back than what was seen, so "the computed index looks negative relative to this
anchor" is **not** proof of unreachability the way it is for a verified base. Tier 1
(alignment) stays exactly as sound regardless — shifting the anchor by a multiple of the
stride never changes the mod-stride result — but Tiers 2 and 3 (which depend on the
index's sign/magnitude relative to the anchor) are **not** safe for these. Every
walking-pointer region now carries `verified_anchor = false`, and Tiers 2/3 are gated on
it being `true`.

**Result: 63 → 72, residual 353 → 344 — a real but modest yield**, smaller than the
dozens hoped for given `berry_projectile_update` alone has 68 residual sites through
`s0`. The complex branching in these functions resets the walking register before the
progression can accumulate cleanly on most paths — reduced recall, disclosed rather than
oversold, same as every other scope limit in this tool. Hand-verified: `0x8005A340` in
`berry_projectile_update`, `region_base 0x800B0D3A` stride `56` — `(0x800A657E −
0x800B0D3A) mod 56 = -12`, nonzero, excluded — and reported `verified_anchor: false`
exactly as designed. Re-validated with the same zero-lost/zero-spurious reconciliation.

### Player-pointer escape closure, and why item 2 still does NOT close (2026-08-01h)

**⚠️ The escape "bound" is a PROVENANCE OBSERVATION, not a proof — corrected 2026-08-01.**
This section previously called it "closed by measurement" and claimed "there is no 'some
unresolved store might have leaked it somewhere' hole." **That was an overclaim.** A
reviewer set out the soundness obligation and my implementation fails three parts of it:

| required rule | `region_provenance.c` as implemented | status |
|---|---|---|
| unconstrained TOP must mean "may be player-relative" | `VTOP` carries `pb_taint = 0` | ❌ TOP enters **untainted** |
| loads / values from unknown memory must not enter untainted | load path sets the destination to `VTOP`; no fixpoint re-run with the discovered destinations marked tainted | ❌ every loaded value enters **untainted** |
| must cover any base reaching the slot after the immediate offset | `val_is_pb` tests only `[0x800A6500, 0x800A65A8)` | ❌ a base reaching the slot via a signed 16-bit offset (±32 KB) is not flagged |

Affine derivatives *do* survive (`addiu`/`addu`/`subu`/`or` OR the taint bit in, and merge
unions it), so the arithmetic half is sound. The load half is not.

**What the measurement therefore establishes:** among values whose provenance the analysis
can track from a literal block-address materialization through affine arithmetic and
merges, **exactly 3 stores carry one** — `0x800454B0` and `0x80045228` in
`sfx_voice_manager` → the SFX voice table `0x80089860`, and `0x80050738` in `play_sound`
→ a function-local stack slot; plus 47 enumerated `jal` argument-passing sites. The SFX
escape is genuine (`sfx_voice_manager` is called with `a0 = 0x800A6500`, and the pointer
is reloaded at `0x80044D88`).

**What it does NOT establish:** that no *other* store carries a block pointer. Any TOP
value, any loaded value, or any value reaching the slot via a large offset could be one
and would not be flagged. Three observed provenance chains ≠ only three values that could
numerically alias the block.

**Why the sound version is blocked on typed pointer sets.** Making the taint sound
requires knowing which memory locations can hold a block pointer, which requires resolving
store *destinations* — and **4,490 stores image-wide have unresolved destinations**. The
inverted formulation does not escape that wall, it relocates it. Neither direction is
sound without typed pointer sets (pool ranges, strides, valid index ranges derived from
allocators/initializers/tables). That makes typed pointer sets **load-bearing for
certification**, not a later refinement.

**Runtime falsification: PASS.** The full census gate (not `--static-only`) ran the
3-fixture writer union on existing fixtures: *"VERDICT: no writer outside the enumerated
set."* No new recordings were required.

**And yet item 2 does not close.** [[Phase 4 - Acceleration Tooling Strategy]] — accepted,
hard-truth-ratcheted — already fixes the operational criterion this campaign kept
treating as undefined:

> The compiler may report a frontier as closed only when the declared universe is
> exhaustive and its **unresolved-intersection set is empty**.

and its promotion linter (`tools/phase4_promotion_preflight.py`) enforces it with a hard
rejection code **`RESIDUAL_INTERSECTS`** for any residual whose `intersects_dimension`
is true. The 251 remaining accesses are unresolved *precisely* in the sense of "may
intersect this slot," so they trip that code by construction. **The bar is empty, not
small, and not "bounded by argument."** Any decision procedure that accepts a non-empty
intersecting residual would be a weaker, parallel standard invented alongside the
accepted one — exactly the failure this campaign has already committed twice.

⚠️ **Do not mark item 2 met on the strength of the escape bound.** It is strong evidence
and a genuine advance; it is not the accepted criterion.

> #### ⚠️ CORRECTION 2026-08-04 (from E16, added without disturbing the reasoning above)
>
> The reading **"the bar is empty, not small, and not 'bounded by argument'"** is
> stricter than any of the three written standards, and it is what stopped this row.
>
> - The **canonical DoD item 2** (`Game Solving Roadmap - From Reconstruction to
>   Reliable Modding.md`) says: *"relevant callers, callees, callbacks, indirect
>   tables, overlays, readers, writers, and downstream consumers have been
>   **enumerated**"*. Enumerated, and scoped to *relevant*.
> - The **Phase-4 exit gate** says: *"No unresolved field, dispatch, asset, or overlay
>   intersects that subsystem's behavior **without being explicitly bounded**."*
>   Bounded — the sentence explicitly contemplates residuals that exist and are bounded.
> - The **"unresolved-intersection set is empty"** line comes from
>   [[Phase 4 - Acceleration Tooling Strategy]]'s *frontier rules*, where it is scoped
>   to a **declared universe** (*"A target declares roots, in-scope images/ranges,
>   explicit boundary owners"*) and is explicitly *"never changes a Phase-4 dimension
>   by itself."*
> - **`tools/phase4_promotion_preflight.py`** reads `claim["residuals"]` or
>   `campaign["bounded_residuals"]` — a **hand-declared** list. `RESIDUAL_INTERSECTS`
>   fires per declared residual whose `intersects_dimension` is not `false`; a
>   companion `RESIDUAL_MALFORMED` requires `boundary` + `evidence` +
>   `next_experiment`. Bounding by *evidenced argument* is the mechanism, not a
>   loophole — the field is literally named `bounded_residuals`.
>
> The caution that produced the stricter reading was well earned (this campaign had
> twice invented weaker parallel standards). But it overshot: it treated the whole
> 2 MB image as the universe and "bounded by argument" as forbidden, when the gate's
> own words are *explicitly bounded* and the linter's own field is
> *bounded_residuals*.
>
> This does **not** revive the escape bound as a proof, and it does not mark item 2
> met here. It says the correct next step for this row is a **declared universe plus
> named, evidenced boundaries**, not driving 192 to zero. Evidence and method:
> `analysis/phase4_e16_bounded_residuals.json`,
> `tools/phase4_e16_residual_boundaries.py`.

**What would actually close it**, in the project's own terms: drive the
unresolved-intersection set to empty. The escape bound says the surface is finite, which
makes that reachable rather than open-ended — the remaining 251 are two named classes
(memory-loaded pointers, `jr`-dispatch entry state) and the tooling to attack them
already exists, accepted but **unmerged**: `tools/phase4_static_frontier.py` (canonical
frontier compiler, resolves 854 `$gp` accesses, joins 1,706 typed-state accesses),
`analysis/phase4_overlay_semantic_index.json` (20 overlay images — directly addresses the
4,967 overlay residual), and `tools/phase4_promotion_preflight.py`, all at accepted
commit `151a5a3bbf07186126a54070e5b2ddc401396e04` on
`ratchet/phase4-acceleration-scheduler-20260801`. Reconciling `region_provenance.c`'s
exclusions into that compiler — rather than maintaining a third independent frontier
tool — is the correct next step.

### The accepted static frontier compiler: a jr-table precision gap (2026-08-01i, corrected)

> **⚠️ This section previously claimed the compiler "silently drops both grants" and
> recommended filing a defect against the accepted tranche. That was WRONG and is
> retracted.** I checked whether the grant *PCs* appeared in the index and, finding they
> did not, concluded silent erasure — without checking whether the *dispatch that reaches
> them* was declared. It is. Correction below.

Evaluated whether the accepted acceleration tooling closes item 2, in an isolated
read-only worktree at commit `151a5a3b`. It does not — but the reason is a **precision
gap, not a completeness defect, and not grounds to reopen the ratchet.**

**What the compiler actually reports for `contact_pickup_walker`:**

| field | value |
|---|---|
| `indirect_jumps` | `[{pc: 0x8005882C, register: v0}]` |
| `unresolved_boundaries` | 47 total — 46 `unresolved_memory` + **1 `indirect_jump` @ `0x8005882C`** |
| unreachable instructions | 104 of 274 |

`0x8005882C` is exactly the walker dispatch: `lui at,0x8002 / addu at,at,v0 /
lw v0,-0x4a90(at)` resolves to **`0x8001B570`**, the documented walker table, and entry
**[10] (action `0x0C`) → `0x800588B0`**, the B06 grant. So the three grant-block accesses
are **downstream of an explicitly declared unresolved control-flow boundary** — not
erased from an otherwise-closed proof. The compiler therefore *cannot* claim closure
through this function, and the accepted contract says precisely this: direct edges are
traversed, indirect edges stay unresolved until a bounded target set is independently
declared.

**The fail-closed path worked.** Item 2 stayed red on `RESIDUAL_INTERSECTS`, no dimension
was promoted, no frontier was declared closed, and both grants remained protected behind
the declared boundary. That is the criterion functioning, not failing.

**What is genuinely true, and useful:**

- On this target the compiler resolves **8** covering accesses; this campaign's census
  resolves **14**. The six extra come from interprocedural argument propagation (the tick
  and its guards — which the compiler *does* declare as `unresolved_memory`, `s1`, offset
  126) and computed-base resolution (both grants).
- At instruction granularity you cannot query the canonical index for "what touches
  `0x800A657E`" and get the grants back — they are absent from `memory_accesses`. That is
  a real precision characteristic to know about when using the index that way.
- `jr`-table enumeration would close the gap. `tools/region_provenance.c` already
  enumerates 39 dispatch tables read-only, including this one.

**What is NOT established, and was wrongly claimed here:**

- ❌ *"Silently drops"* / *"invisible in the output."* False — declared at `0x8005882C`.
- ❌ *A completeness defect requiring the ratchet be reopened.* This is contract-conformant
  behaviour; the tranche never claimed every indirect dispatch was resolved.
- ❌ *Unsafe as frontier authority for every row.* It leaves affected rows open, which is
  the correct conservative outcome.
- ❌ Higher recall alone does not prove the canonical compiler unsound. This campaign's
  extra accesses become authoritative only once their assumptions, target universe, and
  hashes are independently validated — the same bar everything else here is held to.

B06/B08 also sits **outside** the three accepted proof pilots (E15/E08/C13), which the
playbook explicitly scopes as production-readiness demonstrations rather than all-row
coverage. Meeting an unresolved dispatch on a new row does not retroactively narrow that
acceptance.

**The falsifier that would actually justify reopening**: declare and independently pin the
B06/B08 roots *and* the complete jump-table target set, regenerate the claim frontier, and
show the compiler reporting zero unresolved boundaries or an admissible closed frontier
**while still omitting the live grant blocks**. That has not been done and is not implied
by anything above.

**Correct disposition:** file a bounded *enhancement* — `jr`-table target enumeration to
raise target-resolution precision — and contribute this campaign's propagation and table
enumeration toward it. Not a defect, not a revocation, no ratchet reopening.

### Loop-carried merges, a soundness repair, and combined-prover accounting (2026-08-01g)

Three changes in one pass, made while designing the next methodologies at the operator's
request; each was caught or validated by the reconciliation harness doing exactly its job.

**1. A soundness hole in the region tier, found before it could bite.** The tier tested
only `want % S == 0` — the *access starts exactly on the target* case — which is the
**same start-address-only straddle bug** found and fixed in `census_address.py`'s hit
test earlier, reintroduced by me in new code. A width-4 access starting 2 bytes below
the slot overlaps it without starting on it, and a `want` one off either way was being
wrongly *excluded*. The tier now tests the full overlap window
`[want−(width−1), want+target_width−1]` for any multiple of the stride, and Tiers 2/3
require **every** candidate index in that window to be individually unreachable.
**Diffing against the committed artifact: zero previously-committed exclusions were
invalidated** — the hole was real but had not yet produced a wrong claim.

**2. Loop-carried region merges fixed properly.** Two structural gaps: (a) a walking
region meeting its own advanced self (`roff=0` vs `roff=S` after `addiu reg,reg,S`)
collapsed to TOP because the merge demanded exact `roff` equality — the loop killed the
region it had just built; (b) a path still holding the initial CONST pointer meeting the
already-widened REGION collapsed to TOP. Now: same-residue-class regions merge (anchor
kept exact when both are proven literals; **canonicalized** to `0x80000000 + (anchor mod
S)` when not, which is what stopped a reverse-walking pointer from descending the anchor
once per revisit and churning the worklist into the visit cap — that churn was silently
truncating final-round scans, observed as a 149→143 indirect-count wobble, now warned
about and gone); and constants in a region's residue class are absorbed into it, with
`verified_anchor` demoted when a constant sits below the anchor.

**3. Combined-prover accounting.** The absorb can swallow the *player constant itself*
into a walking region — a **precision** loss, never a soundness loss: an absorbed
pointer's candidate index always lies in the overlap window, so a potential real hit can
only fall *into* the residual, never be falsely excluded. But it left 6 sites C-open
that Python's exact constants prove disjoint (`level_load_player_spawn_writer`'s health
writes through `s3` = the player pointer). The harness now treats the two
implementations as what they are — independently sound provers whose exclusions both
stand — and the honest still-open set is *Python's residual minus C's exclusions*. What
must still reconcile exactly, enforced and pinned: identical 14-hit sets, **no C
exclusion colliding with a Python hit** (the catastrophic case), no Python-residual site
left unclassified, and every C-open-but-not-Python-residual site *verified* as
Python-resolved-disjoint rather than assumed benign.

**Result: 72 → 165 excluded (159 alignment, 6 negative-index), residual 344 → 251.**
`berry_projectile_update` alone went 66 → 9 once its walk survived the loop merge.
Hand-verified survivor: `0x8005A360`, canonical anchor `0x80000022` stride 56 — the same
residue class as the contact array (`0x800B0D3A − 0x80000022 = 12933×56` exactly), and
the full window `{681307, 681308, 681309}` contains no multiple of 56.

**What the 251 now are**, by disassembly inspection of the by-function breakdown:
`actor_player_contact_resolver` 38 (bases loaded from memory — actor-list pointers),
`mover_actor_update` 29 + `vm_motion_apply_chase` 26 (entered via `jr`-table dispatch,
so their object-pointer argument is invisible to call-argument seeding),
`player_contact_response` 25 / `player_vertical_update` 15 (loaded actor pointers),
`ground_height_query` 15 / `player_region_poly_query` 14 (plane-record pointers loaded
from the sector table). I.e. the residual is now almost entirely the two classes the
next methodologies target: **memory-loaded pointers** and **jr-dispatch entry state**.

Item 2 is **still not closed**: 251 same-width accesses remain genuinely unresolved,
alongside 149 indirect calls and 4,967 overlay pointer-based accesses. Regenerate:
`tools/phase4_region_provenance_report.py` (builds the C tool, cross-validates, writes
`analysis/phase4_region_provenance.json`).

### Indirect calls: a real capability, a null result, and a precisely named gap

`census_address.py`'s jalr handling previously discarded **every** indirect call
unconditionally, even when the jump-target register's value was already known. Two
capabilities added, both tested (the real image resolves 0 sites this way, so a synthetic
two-function image exercises them): a resolved jalr now propagates `a0`–`a3` like an
ordinary `jal`, and a narrow extension reads a jalr target directly from the pristine
image when it was just loaded from an address *inside the static image* — justified only
for jalr targets (function-pointer tables are effectively immutable here), never applied
to general data.

**Measured on the real image: zero effect.** Every jalr target in the resident image
genuinely fails to resolve by either mechanism — confirmed by disassembly, not assumed.
That's a negative result worth reporting as one, not silently dropping.

**But it narrowed what "indirect calls" actually means for this target.** (The whole-image
figure was 238 before the counting-bug fix above deduped it to 149 — either way, the point
below is about SCOPE, not the raw count.) Of them, only **one** lies inside a function
already known to touch the player block — `vm_motion_apply_chase` (`jalr` at
`0x8004D1E8`, target `lw v0,0x7c(s0)`) — and its argument is `addiu a0,sp,24`, a stack
scratch address, not derivable from the player struct. So essentially none of the
whole-image indirect-call count needs resolving to close *this* frontier argument; the
figure, reported alongside the same-width residual without that context, overstated what
actually gates it.

**The real gap, named precisely.** 8 of the 34 related functions have no `jal` caller
anywhere in the image: `actor_turn_toward_player`, `aimed_object_spawn_sfx`,
`harvester_equip_and_active_update`, `mover_vm_op17_player_proximity`,
`respawn_transition_state_handler`, `sfx_nearest_pickup_f_glue`, `spawn_drop_burst_8`,
`vm_motion_apply_chase`. Disassembling the mover-VM dispatcher
(`event_interpreter_mover_vm`, `0x8004C13C`) confirms at least one is reached via a
`jr` **tail jump** through the documented opcode table (`lui at,0x8002 / addu
at,at,op*4 / lw v0,-0x4d0c(at) / jr v0` → table `0x8001B2F4`, matching Canon), not a
`jalr` call. That's a structurally different shape: `jr` has no return address, so the
callee continues with whatever registers the dispatcher already had live (`s1`, moved
into `s7` just before the jump) rather than receiving fresh arguments. The analysis
propagates calls via `a0`–`a3` only; it does not yet propagate full register state
across a `jr`-based tail dispatch. That is the specific next step for these 8 functions
— not "more indirect calls to resolve."

Regenerate: `tools/census_address.py` (now with jalr resolution) and
`tools/census_pointer_provenance.py`.

## The knockdown site — not part of this subsystem

`0x8004AFB0  sh zero, 0x7e(fp)` in `actor_player_contact_resolver` (`0x8004ABF4`) was
carried for a long time as the **knockdown clear of the power slot**, and as the one
exceptional path DoD item 4 still needed to exercise. It is neither.

### `fp` is the player block **+ 4**

`0x8004AC18 lui v1,0x800A` / `0x8004AC1C addiu v1,v1,0x6500`
materializes the player base directly, then `0x8004AC70 addiu fp,v1,4` makes
`fp = 0x800A6504`. So every offset in the block is shifted by 4:

| instruction | reads/writes | actual address |
|---|---|---|
| `0x8004AF4C  lw 0x2c(fp)` | guard | player+0x30 |
| `0x8004AF2C  lbu 0x9f(fp)` | guard | player+0xA3 |
| `0x8004AF5C  lh 0x7c(fp)` | guard | player+0x80 |
| `0x8004AF6C  lh 0x84(fp)` | guard | player+0x88 |
| **`0x8004AFB0  sh 0x7e(fp)`** | **write** | **player+0x82 — not the slot at +0x7E** |

The frame is internally consistent, which is the strongest check available: `0x8004AFA8
sh zero, 0x80(fp)` writes `0x800A6584` = player+0x84, and that is precisely the field the
guard at `0x8004AEBC` reads *absolutely* (`lui 0x800a` / `lh 0x6584`). The block reads and
writes the same field.

### How two errors hid each other

The original note said the block never executes. That was false — it fires naturally at
frame **5966** of `B08_bubble_repeated_hits_from_boot`, a fixture already in the corpus
when the claim was written; the old zero-event execTrace measured a run that never reached
the region. I then corrected that and asserted the block clears the power slot, which was
*also* false. Each error concealed the other: a site believed never to run could not
reveal that it writes the wrong address.

I also briefly asserted `fp == 0x800A6500` as a **structural check** in
`tools/phase4_knockdown_reachability.py`, reasoning that the function reads the same field
both absolutely (`0x800A6584`) and through the pointer (`0x84(fp)`). That inference is
unsound — those are two *different* fields. Direct pristine-image reads now settle the
base instead: the `lui`/`addiu` pair at `0x8004AC18/1C` materializes the player block and
`0x8004AC70` adds four. The old equality check passed and was wrong, which is worse than
not having it; the replacement is an instruction pin, not a runtime inference.

### How it was caught

A live-power intervention, sound here because **none of the guards reads `+0x7E`**, so
poking the slot cannot change whether the knockdown fires. Poked to 400 at the guard
chain's first pass; the tick ran 399, 398, … and carried straight through frame 5966 —
381 → 380 → 379 — with no write to `0x800A657E`. A breakpoint at the block entry then read
`fp = 0x800A6504` directly.

Every runtime result above comes from a replay whose faithfulness was asserted in the
**same armed run**: the fixture's own grant marker (`-3` at frame 6046) still lands, so
arming the trace did not desync it.

### Consequences

- **Item 4's outstanding exceptional path is withdrawn, not discharged.** There is no
  knockdown clear of this slot to exercise. Item 4 stays ADVANCED pending a re-derived
  exceptional-path list, since the one path this campaign tracked was never a path.
- **Item 2 loses its counterexample.** "The aliased-pointer residual demonstrably contains
  real slot accesses — `0x8004AFB0` lives in it" is **retracted**. No counterexample is
  currently known. That is *not* the same as the residual being empty: 381 accesses still
  have an unresolved base after region provenance (416 before it, corrected from a 2x
  counting-bug-inflated 882 — see the two sections above), so item 2 stays ADVANCED for
  the original reason.
- `0x8004AFB0` is removed from the modelled writer set and from
  `src_re/player_power_slot_800a657e.c`, guarded by a test so the wrong model cannot
  return.

Regenerate: `tools/phase4_knockdown_reachability.py` (static) and
`tools/phase4_knockdown_probe.py` (runtime, with the desync self-check).

## Render descriptors: the tpage/clut writer, partially attributed

`tpage_prim_setup` (`0x8003E4E8`) is a real writer of the scene-dependent descriptor
fields — `0x8003E624` writes `+0x04` (tpage) from `jal 0x80061A48`, and `0x8003E660`
writes `+0x06` (clut) from a base table at `0x800A7DD8` plus bitfields of `+0x08`/`+0x09`.
Its loop covers **pointer slots 115–127**; a post-loop block writes `+0x06` for slots
**32–36 and 41–45**.

It does **not** cover slots **12 (`0x0C`)** and **46 (`0x2E`)** — the two these pickups
use — and a census of those two pointer slots returns **zero** static accesses, because
both the slot and the descriptor body are reached through a computed index. So the
Phase-3 `writer_attribution: unresolved` status is narrowed but not closed, and DoD item 5
stays ADVANCED.

⚠️ Note for anyone extending this: `0x80096B98` is a **128-entry pointer table** (4-byte
slots), not an array of 12-byte descriptors. The bodies live in the gp-addressable data
region. Decomposing that address range by a `0xC` stride produces nonsense — I did it once
before catching it.

## Related

- [[MEM_800A6500]] · [[SYS_grain_harvester]] · [[FUNC_8004A700]]
- [[EXP_2026-08-01_phase4_b06_b08_power_slot]]
- [[Blue_seed_plant_behaviors]] — the pickups that grant these

## B06 bounded-exhaustion closure (2026-08-04)

B06 invincibility is **Substantiated Partial / bounded-exhausted** for valid pristine-retail gameplay. The row-specific C closure compiler enumerates the 14 direct shared-slot sites and classifies all 251 reconciled potential indirect intersections: 29 row-local and 222 cross-system, with zero unexplained sites.

The remaining four local candidates from the earlier frontier are disjoint sine-table or particle-pool accesses. The actor-record proof uses root `0x8009FD80`, stride `0x84`, and the ASM bound `actor_index < 200`; the only congruent candidate would require index `201`. Runtime evidence independently covers grant, protected contacts, the 400-tick countdown, expiry, and post-expiry damage without instrumentation desync.

Evidence: [[EXP_2026-08-04_phase4_b06_bounded_exhaustion]] and `analysis/phase4_b06_closure_20260804.json`. This is bounded exhaustion, not a strict proof over corrupt pointers, malformed assets, or modified executables.

## B08 bounded-exhaustion closure (2026-08-04)

B08 bubble shield is **Substantiated Partial / bounded-exhausted** for valid pristine-retail gameplay. Its address frontier is the same signed halfword as B06, so the sign-independent 251-site C provenance ledger applies unchanged: 14 direct sites, 29 row-local candidates, 222 cross-system candidates, and zero unexplained intersections.

The B08-specific C guard independently verifies blue-x3 production dispatch through type 6, ctor `0x1F`, action `0x2E`, and handler `0x80058998`; unconditional refresh to `-3`; eligible-contact transitions `-3 -> -2 -> -1 -> 0`; the stagger consumption guard; negative values being excluded from the positive timer; the zero/pop damage transition; the three-entry negative-only shell color ramp; and the normal reset path. The former claim that it also verified an exceptional knockdown clear was wrong: that path stores to player+`0x82`, not the power slot.

The retained B08 capsule is complete, untruncated, pristine-media identified, and cycle/frame/RAM/register identical to its control. Existing lifecycle evidence observes the grant, all three absorbs, pop, and post-pop health loss. No additional Interpreter movie is required.

Evidence: [[EXP_2026-08-04_phase4_b08_bounded_exhaustion]] and `analysis/phase4_b08_closure_20260804.json`. This is bounded exhaustion, not a strict proof over corrupted pointers, malformed assets, arbitrary RAM mutation, or modified executables.
