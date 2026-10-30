---
type: experiment
status: complete
date: 2026-08-02
system: enemy AI / D12 worm (id=40) armor + strike
phase: 4
artifacts:
  - analysis/phase4_d12_worm_id40.json
  - tests/test_phase4_d12_worm_id40.py
---

# Phase 4 D12 (worm, id=40) armor, anchor, and strike mechanic

## Question

D12_centipedes_earthworms was unresolved, and named "wall/ground emergence, attack,
immunity, mine interaction" as missing. No dedicated row exists for any single species in
this family in the whole baseline — the operator directed focus specifically to actor
`id=40` ("worm"), which they had direct game knowledge about (a red-berry armor
mechanic).

## Provenance

- Authority: hash-verified pristine retail `SCUS-94288`; ALLMODS not used.
- Fixture: `worm.sav`, media-verified against the pristine disc (`emulator.getStateInfo`)
  before every load.
- Isolated instance: config `/tmp/duckstation-debugger-d12`, port `23505`, never the
  operator's own; stopped via the launcher at the end.

## Method

**Identity**: read the live actor record directly, then dereferenced the runtime-record
backlink for the type-word — a second, independent field.

**Armor sweep**: same method proven for D13/shell_bug — fresh `emulator.loadState` per
berry class, equip index poked directly, one throw via a `debugger.resume` +
`emulator.pressButton{seconds}` + `debugger.pause` sequence, then read `hp` after a
90-frame window.

**Stationary/anchor check**: watched 240 frames with no interaction (baseline), then
attempted a position poke (the method proven safe for shell_bug/Redbug) to see if the
worm would tolerate relocation.

**Strike mechanic**: since the worm resisted repositioning (see Result), moved Flik
instead — its own validated Y, `pos`/`prev_pos`/velocity all written together (the D09
lesson: writing `pos` alone lets the game's own per-tick integrator snap it back). Placed
400 units from the worm (inside the documented 700-unit `op17` radius) and sampled Flik's
true health (`0x800A6594`) and the worm's own state every 5 frames.

## Result

**Identity**: `id=40`, runtime type-word `0x2528` — matches `Enemy_spawn_architecture.md`
exactly.

**Armor**: red does zero damage (HP stayed 8 across 120 frames). Blue/homing: `-2`. Gold:
`-4`. Mega: `-3`. Exact match to D13/shell_bug's own result and to the already-documented
generic hit-tail switch (class 0/12→`-2`, 127→`-4`, 128→`-3`). This takes the
berry-tough-blocks-only-red finding from a single species to a confirmed general rule.

**Stationary/anchored**: zero position change over 240 frames despite `vm_ip` actively
cycling every ~60 frames. A position poke snapped back to the worm's own anchor within a
single 30-frame check — a stronger tether than shell_bug showed.

**Strike (new territory — not previously live-tested for this row)**: Flik's true health
dropped `4→3` within 5 frames of coming within 400 units, with a strong knockback impulse
launching Flik to 12,000+ units of separation within 30 frames. This directly explains a
repeated "unexplained drift" artifact observed in earlier sessions the same day (the D09
and D13 work) — it was strike knockback, not a bug or residual-physics glitch. The worm's
own `hp` stayed exactly 8 (not a mutual-damage contact). Only one strike landed before the
knockback carried Flik out of range.

**Campaign breadth**: worm (`id=40`) confirmed in 5 levels — `LEVEL01`(3), `LEVEL03`(2),
`LEVEL07`(4, coexisting with D13's shell_bug in the same disc directory), `LEVEL08`(4),
`LEVEL10`(4) — 15 records, zero variants. Bonus (not pursued further): earthworm
(`id=12`, the row's own namesake) is confined to `LEVEL03` only (11 records, zero
variants).

**Strike mechanism, traced statically (added same day, after the operator asked whether it
was worth digging into the ASM)**: rather than starting a fresh MIPS disassembly hunt,
checked already-decoded static data first — `analysis/vm_programs.md`'s bytecode around the
`vm_ip` values observed live. The trigger reads `player_proximity[700]` → in-range branch →
`flags_mask` sets `+0x5c` bit `0x40` → `call_native[8]` → native `0x80057b84`. A second,
near-identical window later in the same program uses `player_proximity[1200]` and the same
native — two proximity-strike windows per cycle, not one. `0x80057b84` was **already
decompiled in this repo** (`src/main/80057b84_vm_native_aimed_drop_spawn.c`,
`vm_native_aimed_drop_spawn`) with a single caller (the VM's own `call_native` dispatcher,
confirmed via `analysis/phase3_call_graph.json`). It spawns a burst of 8 objects cycling
kinds `21/22/23` at the *caller's own position* via `spawn_drop` (`0x80059e44`, the same
function used for gold-berry/pickup drops), then aims that burst's facing at the player —
but only because the caller's `id == 40` is hard-coded in the native; every other caller
gets a generic descriptor-byte facing instead. **This means the STRIKE is not a direct
`contact_vs_actor_handler` hit** (the function searched twice already this session for the
berry-tough gate PC, both times more tangled than expected) — it is a distinct code path,
an aimed spawn of drop-type objects. The 1-point true-health hit and knockback measured
live almost certainly come from Flik's own contact with one of those spawned objects, not
from the worm's own record. Not traced: the handler that applies damage/knockback from a
spawned kind-21/22/23 object on contact with Flik, and those kinds' own visual identity.

**Respawn test (added same day)**: same method as D09/Redbug and D13/shell_bug. Killed a
fresh `worm.sav` with four blue-berry hits (`8→6→4→2→0`) — 8 of 12 throw attempts missed
and were retried, since Flik's aim drifts between un-reloaded throws (unlike the single
fresh-reload-per-trial armor sweep). HP passed through the `999` death sentinel before
clearing to `0`, `id` staying `40` (temporary-KO shape). Watched 4000 frames (~66s): `hp`
stayed `0`, `id` stayed `40` throughout — no revival. Negative, matching both prior
species exactly; now confirmed for 3.

### ⚠️ RETRACTED — the "no respawn" conclusion above was wrong

The operator pushed back with direct gameplay knowledge: the enemy *does* come back, but
never while Flik stays near it — only after Flik leaves and returns. The test above never
tried that; it kept Flik stationary the entire time. Re-tested live: killed a fresh worm,
had Flik walk away using real controller input (`debugger.resume` + `emulator.pressButton`
with a real held direction, not a position write) far enough (~76,000+ units, reliable
across repeat runs), and watched — `hp` reset to `8`, `id` stayed `40`, `flags` and `vm_ip`
returned to values consistent with a fresh spawn. Confirmed live for worm and, separately
the same day, for Redbug (D09). shell_bug (D13) shares the identical original flawed test
design and is retracted on that basis, though not independently re-run live this pass.

## Respawn mechanism, ASM-traced (added later the same day)

Live-timing experiments to pin an exact trigger distance turned out unreliable (real-world
`time.sleep()`-based control of both the walk and the watch window produced inconsistent,
non-monotonic results — e.g. one run reached *farther* than a successful run yet failed to
trigger). Switched to reading the actual code instead, per the operator's suggestion.

**Position pokes never reproduce the reset**, tried three ways: (1) a single one-time
teleport followed by 50 real seconds of continuous `debugger.resume` with no further
writes; (2) a teleport deliberately constructed with a "real" one-frame `prev_pos`→`pos`
delta, matching what an instantaneous large real step would look like; (3) many small
per-frame position increments written every frame via `debugger.scatterWrite` +
`emulator.advanceFrames{frames:1}`, reaching over 111,000 units total. None triggered it.
Only genuine continuous execution with real controller input ever did.

**The reset write, caught live**: armed `accessLog.addWatch` (type write) on the worm's own
`hp` field *before* a real walk-away, then captured the exact instruction:
`sh v0, 0x6e(t0)` at PC `0x80049ca4`, writing hp `0 → 8`.

**A near-miss in attribution, caught before banking.** The containing address range
(`functionBounds` reports one merged span, `0x800498AC`–`0x80049E84`) is already Canon —
`FUNC_800498AC_enemy_update_deathanim`, a bitmask-flag function with a regression-tested,
documented contract (`1` = death-animation update, `2` = terminal retirement: clears hp to
`0`, clears id, removes from the live table). A first draft of this finding attributed the
reset to that function's own `a1=2` branch. That's backwards — `a1=2` clears hp, it doesn't
set it to `8` — and was caught by noticing the captured write uses register `t0`, not `s0`,
the register the documented branches use throughout. Re-disassembling the full span found a
real function boundary hiding inside the "one" merged function: a `jr ra` return at
`0x80049C28` immediately followed by a clean new routine at `0x80049C2C`
(`addu t0, a0, zero`). Everything from there on is a **separate, previously undocumented
routine** — flagged directly on the `FUNC_800498AC` Canon page as a tooling pitfall so it
doesn't happen again.

**What `0x80049C2C` actually does**: reinstantiates the actor fresh from its own
spawn-chunk template, dereferenced via the runtime-record backlink (`+0x80`, already
documented elsewhere): id from backlink`+0xc`, position X/Y/Z from backlink`+0/4/8` each
shifted left 5 (matching the documented `record XYZ<<5` spawn-anchor law exactly), the
mover-VM program pointer via a lookup into the 13-entry program table at `0x80077AF8` keyed
by backlink`+0xd` (matching the program-table-index discovery already banked under D13),
hp from backlink`+0x10` (the captured write), and flags from backlink`+0x12`. A genuine
from-scratch re-instantiation, not a state toggle — explaining why the revived worm's
`vm_ip` landed near the mover program's own start rather than resuming where it died.

**A separate, related mechanism was also traced**: a per-actor per-frame update function
(`0x8004D224`–`0x8004D6A4`) maintains a countdown timer at each actor's own `+0x4A` signed
halfword. At death, `FUNC_800498AC`'s own `a1=1` branch runs a per-species jump table
(keyed on `id-6`) that writes a negative constant there (observed: `-24`, `-33`, `-16`,
`-25` for different id ranges); each frame this update loop processes that actor, it
increments the counter toward zero and calls `FUNC_800498AC`'s `1`/`2` branches the instant
it crosses zero. This timer mechanism is real and confirmed, but its exact causal link to
`0x80049C2C` firing was not established live.

**Two residuals named explicitly, not glossed over.** (1) `0x80049C2C` has zero static
callers (`debugger.xrefsTo` finds none — it's reached via an indirect/computed jump) and an
`execTrace` watch armed on it produced zero hits in a run where the reset demonstrably
fired — almost certainly an `execTrace` reliability gap under this project's usual
resume/pause driving pattern (the identical 0-hits-despite-a-real-event pattern was hit
once already this session, tracing a wall_worm throw dispatch), not evidence the routine
wasn't reached, but the exact caller/trigger remains unconfirmed. (2) The same per-frame
function also contains an earlier pass that admits actors into the live table
(`0x80090748`) based on squared distance to a cached anchor point (`0x8009EC50`) versus a
per-actor radius — and `xrefsTo` on that anchor traces its one writer to a function that
populates it from the **camera's own tracked state** (`camera_follow_update`, already Canon
elsewhere), not Flik's raw position, which is a plausible reason position pokes never
worked. But read literally, admission requires being *within* the anchor's radius, which
would mean staying near should tick the timer and walking far should freeze it — the
**opposite** of the confirmed behavior. This contradiction is not resolved, and it's not
even confirmed that this admission check is the right code path to explain the reinit at
all — named as an open question rather than forced into a tidy story.

## wall_worm (id=41) sweep (added same day)

Directed next after worm was closed out — no live testing existed for wall_worm at all, and
it directly tests whether the `id==40`-hardcoded aim special-case in
`vm_native_aimed_drop_spawn` means it behaves differently. Isolated instance, port 23507,
config `/tmp/duckstation-debugger-d12-wallworm`, stopped via the launcher at the end.
Fixture `wall_worm.sav`, media-verified, located via the same live-pointer-table scan
filtered for `id==41` (slot 0, base `0x800a0098`).

**Identity**: `id=41` (`Enemy_spawn_architecture.md`: `wall_worm 0x2629 -> 41`). Initial
state bit-identical to worm's own (`hp=8`, `flags=0x4045`), `vm_ip` on load sits inside the
exact same shared bytecode block worm executes.

**Stationary**: confirmed, 240 frames, zero movement.

**Armor**: blue/homing `-2`, gold `-4`, mega `-3` — exact match, a 4th confirmed
berry-tough-family instance. Red: 6/6 attempts showed no hp change, consistent with the
rule, but an attempt to independently confirm the throw connected (an exec-trace watch on
the throw dispatch `0x80047170`) returned 0 hits across 5 further fresh-load trials —
inconclusive on its own (0 hits even though throws demonstrably work on this exact fixture
for the other 4 classes), so this result carries an explicit caveat rather than standing as
an independently re-proven third case.

**STRIKE — tested at two distances, CONFIRMED NEGATIVE.** 400 units (well inside both the
700 and 1200 unit radii): 400 frames, 2 full loop cycles, no strike. 80 units (near
point-blank): 600 frames, ~2.5 loop cycles, still no strike. `vm_ip` was directly observed
sitting at the proximity-check instruction itself (`0x80077a70`) with the very next sample
already past it, in-range branch not taken — the check was *reached and evaluated false*,
not merely never reached. Since both actors share identical bytecode and baked-in radius
literals, the most likely (not live-confirmed) explanation is that wall_worm's true
render/hitbox position differs from its `+0x28` anchor field, plausible for an actor that
may spend part of its cycle embedded in a wall. Either way: **a real, well-tested behavioral
divergence** — wall_worm does not strike Flik under conditions that reliably strike worm
within ~30 frames.

## Reproduction

```bash
python3 -m pytest -q tests/test_phase4_d12_worm_id40.py
```

The live portions (armor sweep, stationary check, strike measurement) are not yet
scripted into a single runnable tool — all were unrecorded manual play this pass.

## earthworm (id=12) sweep (added same day) — the row's own namesake, last untested species

Identity confirmed live (`id=12`, matches `Enemy_spawn_architecture.md`). Max hp is `1` —
too little to distinguish per-class damage amounts the way worm/shell_bug's multi-hp pools
did.

**No strike mechanic, confirmed for free from already-decoded static data**:
`analysis/vm_programs.md` already has a dedicated `## earthworm @ 0x800775c8` section — a
plain `wait_random → random_dir_step → park_seek → jump_back` wander loop, no
`player_proximity` opcode, no `call_native`. Earthworm doesn't run worm/wall_worm's shared
ambush block at all.

**Armor — a genuine methodology miss, then corrected.** First attempt reused the ~1.6s
post-throw wait that worked for every other species this row and found 0/6 landed for
homing. The operator corrected this twice: homing *does* connect, it just takes a couple of
real seconds to travel — not a facing problem for homing specifically. Re-run with a longer
watch (checked every 0.5s): the throw connected at +2.0s, hp `1 → 0`. Homing does full
damage.

**Red/blue/gold/mega were not independently live-confirmed.** A reposition attempt (offset
Flik via the earthworm's own `+0x28/2c/30` anchor field) produced a visually wrong
placement — caught by the operator watching the actual emulator window, not by anything in
the numbers ("you're moving flik up vertically when he should be shifted back a bit"). A
`captureFrame` screenshot of the fixture's own *default* position then showed Flik already
standing directly next to the earthworm — no repositioning was needed at all, the anchor
math was simply wrong. Even from that confirmed-good default position, straight-aimed
throws (red/blue/gold/mega) don't land; the operator explained this is a facing/aim-cone
problem distinct from homing's acquisition-based targeting, and directed against forcing it
further live. **"There is no armour for the little earthworms that appear in the tunnels"**
is the operator's own direct real-gameplay observation, stated independently of and before
this session's live testing — banked as testimony, explicitly distinguished from the
live-confirmed homing result above.

**Method lesson**: the earthworm's own `+0x28/2c/30` anchor field is not safely comparable
to Flik's own `0x800A6500` coordinate space without further validation — the numeric offset
looked reasonable (a ~44,000-unit Y mismatch against a screenshot showing them on the same
visible ground says otherwise). Worth remembering before doing cross-species position math
again.

## Residuals

earthworm's red/blue/gold/mega armor result — relies on operator testimony only, not
independently live-verified (no working reposition/reorientation method found for this
fixture); wall_worm's own respawn test and campaign-breadth scan (armor + stationary +
strike done, these not); WHY wall_worm's proximity check evaluates false
(render-vs-anchor-position hypothesis, not confirmed); mine interaction (named in the row's
own scope, not tested); the exact strike-trigger radius boundary for worm (now known there
are TWO windows, 700 and 1200, not distinguished live); whether repeated strikes are
possible without the knockback removing Flik from range; the contact handler that applies
damage/knockback FROM a spawned kind-21/22/23 object to Flik (the native call itself is
traced, this last hop is not); kinds 21/22/23's own visual/render identity; wall_worm's
red-berry throw-connectivity caveat; the second native (`0x800b3f00`, called elsewhere in
the same shared program's tail) never investigated; full lifecycle beyond in-session
respawn (level-reload restoration untested, same as D09/D13 — close to tautological given
the loader architecture); a scripted/recorded oracle; cross-system audio; source closure;
the exact caller/trigger of the reinit routine `0x80049C2C` (unconfirmed, `execTrace`
proved unreliable); the admission-radius contradiction in the distance-based live-table
check found alongside it; worm's own exact `+0x4A` countdown constant (the per-species
jump table was read but worm's specific case not isolated).

## 2026-08-04 bounded-exhaustion correction

### Disposition

D12 is **substantiated partial and bounded-exhausted for Phase 4**. Move on. No
additional Interpreter movie is required for the currently named gaps. The
machine-readable correction is
`analysis/phase4_d12_bounded_exhaustion.json`; the fail-closed pristine-ASM guard
is `tools/phase4_d12_closure.c`.

No relevant retained D12 capsule exists in the Phase 4 capsule set. This pass
therefore did not promote a capsule or start a live replay: register flow, direct
call xrefs, constructor metadata, and the respawn predicate are all executable
static domains.

### Observation: worm burst kinds 21/22/23

Native `0x80057B84` really does create eight contacts cycling constructor kinds
21, 22, and 23, with id 40 receiving the player-facing aim. Their pristine rows
select contact-walker actions 5, 6, and 5.

The contact walker initializes `s6=0`. Those actions reach the default block at
`0x800589D4`, which retires the contact with countdown 12 but does not set
`s6=1`. The player-damage call `0x8004A700` at `0x80058A48` is guarded by
`s6==1`, so all three spawned kinds branch around it.

### Causal correction: the old 4 to 3 health event

The prior inference that the spawned burst "almost certainly" caused Flik's
health loss is falsified. Kinds 21/22/23 do not damage Flik through their contact
walker path. The observation was made after placing Flik close to the worm and
matches the already-established ordinary actor-body-contact path, including the
one-health loss and knockback. That body-contact attribution is a bounded
inference, not a retroactive exact-PC trace of the historical event.

The native burst remains confirmed behavior, but D12 no longer calls it a proven
damaging ranged strike. Its exact visual identity is presentation-only residual
work.

### Causal correction: respawn owner and trigger

The old zero-static-caller result was a tooling miss. An exhaustive C scan of
pristine executable JAL targets finds exactly two direct calls to `0x80049C30`:

- `0x8004A664`, initial actor-pool construction
- `0x8004D3F0`, dead-actor reinitialization in the mover scheduler

The alleged near/far contradiction is also resolved. For a dead actor whose
reinit delay has expired, the scheduler calls oriented camera-containment test
`0x80025084`. A nonzero result suppresses reinitialization. A zero result, meaning
the spawn is outside that camera containment volume, reaches `0x8004D3F0`.
Walking the camera away therefore permits reinitialization; returning later
admits and displays the fresh worm. This is not a raw Flik-distance predicate,
which explains why direct player-coordinate pokes were misleading.

The reinit countdown is actor halfword `+0x62`, not `+0x4A`. Reinitializer
`0x80049C30` copies spawn-descriptor byte `+0x11` into actor `+0x62`, with
special-case adjustment logic. Actor `+0x4A` belongs to the separate death
animation/retirement lane. Enumerating every authored descriptor byte is now a
low-return data census rather than a mechanism gap.

### Mine Plant interaction

The Mine Plant blast uses constructor 56. Its collision tuple has damage class 0
and permanence marker 6. Against the worm's local HP 8, the ordinary damage
dispatch subtracts 2, producing HP 6. One mine is therefore not an instant kill.
The permanent-death bit and quota decrement matter only when a mine hit is
lethal.

This closes the named D12 mine residual without species-by-species live replay.

### Closure boundary

Closed for Phase 4:

- id-40 identity, anchored stationary behavior, armor matrix, and campaign breadth
- native burst owner, count, constructor cycle, id-40 aiming, and non-damaging final hop
- direct respawn callers, camera-containment polarity, and actual delay field/source
- Mine Plant damage amount, survival result, and lethal-only permanence boundary
- the retained wall-worm and grub findings, including the id-12 grub correction

Low-return residuals:

- exact PC attribution for the already-observed historical body-contact event
- visual identity and presentation timing of burst kinds 21/22/23
- enumeration of per-spawn descriptor byte `+0x11`
- why wall-worm id 41's VM proximity predicate evaluates false
- wall-worm respawn breadth, genuine-earthworm taxonomy, and cross-system audio

Reopen only if a MOD depends on one of those residuals or full runtime promotion
is explicitly required. For exact body-contact attribution, the narrowly scoped
fixture would be a normal-speed Interpreter movie placing Flik near an id-40 worm
without throwing a berry, traced at `0x8004A700` and its actor-contact callers.
That movie is not needed for the present bounded-exhaustion disposition.
