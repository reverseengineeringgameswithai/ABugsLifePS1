---
type: experiment
status: complete
date: 2026-08-02
system: enemy AI / D20 Hopper boss
phase: 4
artifacts:
  - analysis/phase4_d20_hopper.json
  - ObsidianVault/Canon/Systems/Enemy_AI_state_machine.md
  - ObsidianVault/Canon/Systems/SYS_enemy_ai.md
  - ObsidianVault/Canon/Functions/FUNC_8005038C_scene_setup_and_load.md
  - movies/Phase4/Interpreter/Hopper_white_berry_death.movie.json
  - movies/Phase4/Interpreter/D20.movie.json
  - src_re/enemy_ai_programs.c
---

# Phase 4 D20 Hopper — identity corrected, combat and finale traced to shared generic machinery

## Question

D20_hopper was fully `unresolved`, the only row of that status not related to Molt
(explicitly avoided this pass — another agent is working it) or already covered by other
rows this session. Existing, never-indexed fixtures sit at the repo root:
`hopper_boss.movie.json/_1/2` (v1 format, digital-only, 2026-06-22) and
`hopper_throwing_white_berry.sav`.

## Identity: the archived note's claim is wrong, and it's the same mistake already caught for Thumper

`ObsidianVault/Archive/Superseded/Systems_Enemy_AI_state_machine.md` claims Hopper "is
NOT a bespoke boss — he REUSES the chaser AI... Actor = chaser slot `0x80095358`, driver
`FUNC_8004DF18`." That same file's own later Thumper correction (residual #5) found the
identical claim shape wrong for Thumper: `0x80095358` is the CAMERA, not a boss actor —
Thumper is really a chunk-31 actor, id 16. The Hopper section predates that fix (written
2026-06-22, corrected 2026-07-03) and was never revisited.

Loaded `hopper_boss.movie.sav` and `hopper_throwing_white_berry.sav` (both `scene_id=15`,
matching `F15_canyon_showdown`) into an Interpreter-mode isolated instance. Scanned the
chunk-31 live actor table (`0x8009FE04`, stride `0x84` — the same base already correct for
Thumper) and dereferenced each record's `+0x80` backlink into the spawn-descriptor table
for the real type-word (low byte = actor id, cross-validated against id=30/bird → 0x1d1e
and id=15 → 0x150f, both correct).

24 live records, 4 distinct ids: `id=11` (movable seed, already-established generic
class) · `id=15` (15 instances, uniform hp=6 — an undifferentiated background actor, not
yet identified elsewhere, clearly not a unique boss) · `id=30` (the already-Canon D17 bird
boss, hp=101, matching the archived note's own correct observation that a bird-eats-Hopper
cinematic ends the fight) · **`id=22`** — the standout: a SINGULAR instance, genuinely
live/moving (position changed every sampled frame across movie-relative frames 3600-3700),
52,127 units from Flik in the white-berry-throw save, at a Y level near Flik's own rather
than the earlier deep-chasm Y seen in the other save (consistent with different fight
phases). A captured frame from the white-berry save (absolute frame 234340) shows a
distinctive large orange/tan figure at a distance, boss-shaped, in a fixture literally
named for Hopper's own attack.

`gpu.pickObject` could not independently confirm this — it hits the same known limitation
already documented for Thumper (`this fork's pickObject returns the transformed-vertex
render buffer, not the actor RAM address` for this rendering pipeline). Identity is
high-confidence from the live/singular/positional/visual convergence, but not closed to
the same certainty Thumper reached via disassembly of its manager function — a reasonable
next step if more certainty is wanted.

## White-berry producer chain, self-recorded and traced live

Operator, directly: *"I'm assuming we're gonna have to do a new Interpreted movie for
Hopper right?"* — confirmed yes for any live-instrumented work, given the existing v1
movies are digital-only and pre-date the Interpreter-desync fix. Rather than needing a
manual playthrough for this narrow slice, `hopper_throwing_white_berry.sav` already sits
at the exact moment Hopper commits to the throw, so a fresh movie was self-recorded from
that anchor: `movie.startRecording` with `start_state` + `load_start_state:true`, no
scripted navigation needed. Saved as
`movies/Phase4/Interpreter/Hopper_white_berry_death.movie.json` (642 frames, v4, new file).

Over the captured sequence `id=22` closed distance on Flik from ~40,000 to ~8,000 units
(confirmed pursuit, not coincidence) while Flik took 3 hits and died — hp 3→2→1→0→−1,
lives exhausted. **Damage side closes against already-Canon code**: `debugger.addBreakpoint`
at `FUNC_8004A700`'s entry (`0x8004a700`) + `$ra` trace across all 3 hits found two came
from `0x80058A48` — the SAME `contact_walker` (`FUNC_800586B0`) caller D15's web attack
uses — and a third, landing one frame after the first, came from `0x8004B4A0` (an
already-Canon direct-contact resolver): a projectile hit and a body-contact hit within 2
frames of each other, not one mechanism. No new damage-side callers — both are fully
Canon already.

**Projectile identified**: scanning the contact pool across the hit window for a record
closing distance on Flik while approaching from well below (an arcing trajectory) found
slot 10, `action_id=2`, closing 4352→1281 units across 2 frames immediately before the
hit. A second record (`action_id=7`) spawned at nearly the identical position the instant
the first connected — almost certainly an impact/splash effect, not a separate mechanism.

**Spawn side traces to the SAME sibling allocator D15 already fully decoded.**
`accessLog` on slot 10's own `action_id` field found the write at `0x8005a1d8` —
literally the same instruction PC already traced for D15's web attack and already-Canon
for the unrelated berry-throw system (`0x8005A0E0`, `FUNC_80059E44`'s "explicit
constructor" variant). This confirms that allocator is genuinely generic across species
and systems, not anything Hopper-specific.

**The spawn caller sits in the SAME unresolved overlay region the archived note already
named for Thumper.** `debugger.addBreakpoint` at `0x8005a1d8` + `$ra` trace, sampled
across the fight, consistently found the white-berry spawn coming from `0x800b46d4`
(call at `0x800b46d0`, fixed metadata pointer `a1=0x80079a34`). This address is inside
`~0x800b3c04-0x800d1570` — exactly the range the archived
`Systems_Enemy_AI_state_machine.md` names OPEN for Thumper's own combat fields ("all
three live in the boss COMBAT OVERLAY `~0x800b4xxx`"). Two more overlay-resident spawn
sites turned up incidentally in the same trace: `0x800b4934` (`action_id=50`, plausibly a
landing/hop-dust effect given Hopper's leaping movement) and `0x800b4a40` (`action_id=52`,
a very frequent generic ambient-dust action_id also seen as Flik's own movement trail
elsewhere this session).

`transferLog.resolve` on `0x800b46d4` returned no provenance ("no covering load-map
segment, decompression record, or DMA/CD-ROM history") — the overlay was already resident
before this session's instance connected, since it was loaded via a `.sav`, not a live
boot, so no transfer event exists to identify the file. `debugger.functionBounds` returned
`confidence:"low"`, a 121,200-byte merged region spanning `0x800b3c04-0x800d1570` — far
too large to be one function and not yet function-census'd. Closing this needs a
cold-boot capture with `transferLog` armed before the canyon-showdown overlay loads.

## Operator-recorded full fight — bird-nest finale located

Operator: *"okay i recorrded a new movie in interpreter for your reference for later"* —
an independent, much longer recording than the self-recorded throw-to-death slice above:
`movies/Phase4/Interpreter/D20.movie.json` + `.sav`, 16,711 frames (~9+ minutes), format
v4, a fresh play session (not anchored to `hopper_throwing_white_berry.sav`).

A poll-only survey (no instrumentation armed — `movie.advanceToFrame` + memory reads +
periodic screenshots) found lives drop from 9 to 7 across the recording. Operator,
directly: *"the death / damages on my part was poor gameplay, nothing to do with solving
Hopper"* — noted for completeness (the accompanying hp-drop-then-reset pattern is real and
matches the self-recorded slice), but not itself a mechanic finding. All of this stayed
within `scene_id=15` until late in the movie. At movie-relative frame ~16100, a screenshot
shows a distinct scripted cinematic — a large red/orange bird in a nest, wings extended,
with a smaller creature — almost certainly the bird-eats-Hopper finale the archived note
names as never decoded ("the bird setpiece `FUNC_8004DD98`... this would confirm it in
its real Hopper context"). `scene_id` (`0x80082504`) transitions from 15 to 0 somewhere
between frames 16100 and 16300 — not narrowed further this pass (movies don't support
rewinding once advanced past a target frame, so a tighter bisection needs a fresh reload,
and this session was already very long). By frame ~16700 a genuine "level complete" screen
is on screen (10/50 grain, 2/4 FLIK letters, 00/16 seed tokens) — confirming the recording
captures Hopper's actual defeat and the stage completion, not just combat.

This single fixture likely has enough to close several remaining open items in one
follow-up pass: the exact finale trigger (now narrowed to a ~200-frame window instead of
16,711 frames), its connection to `id=22`'s own state at the moment of defeat (by analogy
to Thumper's `0x80090bee`/`0x80090bec` defeat-flag pair), and the ending transition past
level-complete. Not yet touched: whether the recording distinctly covers ground/flying/
tracking phase transitions or barrier/retreat mechanics.

**Scope correction: the Atta chase is not part of this row.** This pass's own earlier
speculation ("may not be part of this specific encounter") is now resolved — operator,
directly: *"Atta is not in this stage as that is LEVEL 14, this was only level 15."* Atta
belongs to Stage 14 (`F14_riverbed_flight`'s own subject), not D20_hopper's stage-15
canyon-showdown material at all.

## Finale trigger traced to an exact instruction

Operator: *"got it. I'm assuming you'll need to drill deeper into this recording to do
exhaustive Phase 4 work?"* — confirmed, and proceeded to bisect and instrument the window.

Reloaded `D20.movie.json` fresh in a new isolated instance (`/tmp/dsrepro-d20deep`, port
23600). Movies can't rewind, so each narrower window needed a fresh reload; bisected
forward-only from the known 16100-16300 range down to a 5-frame window (16165 scene=15,
16170 scene=0). Armed `accessLog` write-watches on `id=22`'s own hp/flags/id fields, on
Thumper's own known defeat-flag pair (`0x80090bee`/`0x80090bec`, to directly test reuse),
and on `scene_id` itself, then advanced through.

Found the exact write: absolute frame 36166 (movie-relative 16166), PC `0x800503ac`,
`sw zero, 0x2504(at)`, `scene_id` 15→0. `debugger.functionBounds` identifies the enclosing
function as `0x8005038c-0x800503fc` (116 bytes, confidence exact) — which already has a
full Canon page, `FUNC_8005038C_scene_setup_and_load.md`: a GENERIC, whole-game
scene-transition dispatcher ("wraps display-buffer init + DAT resource load for entering
a scene"), not anything Hopper- or boss-specific. It saves the old `scene_id`, zeroes it
as a loading guard, conditionally sets a target-scene field and calls
`display_buffers_init`/`resource_id_dat_load_dispatcher`, calls a fixed overlay entry
point (`0x800b96e4`), then restores `scene_id`. Live disassembly also caught and corrected
a stale address in that page's own evidence (`0x800823ac`, not the previously-stated
`0x800821ac`).

That function's own documented callers are `main_shell_state_machine`,
`scene_flow_dispatcher`, and `fmv_sequence_completion_check` (`0x800502c4`, immediately
adjacent) — the last is the strongest candidate for the actual Hopper-defeat trigger,
since it already sums a 16-entry completion-flag array and, on a specific total, calls
`fmv_bin_load` then `scene_setup_and_load` ("cutscene/condition finished, transition
scenes"). Which of the three fired this specific invocation was not confirmed this pass —
would need a breakpoint armed at `scene_setup_and_load`'s entry *before* frame 36166,
which means another full reload from frame 0.

`id=22`'s own hp (`+0x6e`) and id field received **zero write events** across the entire
~30-frame instrumented window — Hopper's record is not despawned or health-modified at
the moment of defeat. Confirmed separately at mf16170: still `id=22`, `hp=20` — a static
value matching what was seen in the *unrelated* `hopper_boss.movie.sav` from a different
session, never fluctuating within this session either. Suggestive of (not conclusive
proof of) the archived note's disputed "No HP bar" claim. Neither of Thumper's own
defeat-flag addresses received any write — a clean negative result: Hopper does not reuse
that specific mechanism. `id=22`'s flags field toggles a repeating 2-bit pattern every ~2
frames throughout the window via generic-looking low-address PCs — reads as a routine
visual blink effect, not obviously defeat-specific, not chased further.

**Net assessment**: every mechanism traced across this three-pass session — `contact_
walker`, `FUNC_8004A700`, the sibling contact allocator, and now `scene_setup_and_load` —
turned out to be shared, whole-game-generic machinery, not bespoke boss code. D20's core
combat/defeat mechanism is judged BOUNDED/substantially exhausted; the remaining caller
question, the white-berry overlay's own file identity, barrier/retreat, the `+0x6e`
question, stage-13 breadth, source closure, and audio are well-scoped last-mile items.

## Reproduction

```bash
python3 -m pytest -q tests/test_phase4_d20_hopper.py
tools/launch_repro_playback.sh --config-dir /tmp/dsrepro-d20hopper --port 23590 \
  --token debugger-1000 --disc "Disney-Pixar A Bug's Life (v1.0).cue" \
  --execution-mode Interpreter
```

The existing v1 movie fixtures are digital-only and predate the analog-stick and
Interpreter-desync fixes — `hopper_boss.movie2` is only faithful for its first ~3,745
frames before Flik dies from unrecorded analog steering. Both `Hopper_white_berry_death.
movie.json` (self-recorded) and the operator's `D20.movie.json` (Interpreter, v4) are safe
to instrument freely. Prefer save states for poll-only identity work; anything needing
`accessLog`/breakpoints needs an Interpreter-recorded movie first. `D20.movie.json` cannot
be rewound once advanced past a target frame — reload fresh to bisect an earlier window.

## Aggro/chase mechanism confirmed — and a self-correction (2026-08-03)

Operator, directly: *"did we exhaust his aggro nature where he chases Flik?"* The honest
answer at that moment was no — only the observable RESULT of chasing (closing distance)
had been confirmed; the underlying gate/driver had never been traced. That is a real
correction to what I'd just told the operator, not a new finding layered on a correct
prior answer — my own immediate answer minutes earlier ("no aggro flag/gate found... not
traced") was wrong, and it was wrong because the investigation hadn't gone deep enough,
not because the mechanism doesn't exist.

It turns out the general chase mechanism was already fully solved and
live-falsification-tested in `src_re/enemy_ai_programs.c`, committed 2026-07-03 — a full
month before this session started. Every regular enemy runs on the shared mover-VM
(`FUNC_8004C13C`); its motion-apply phase (`0x8004c8ac`+) has a GLOBAL chase gate at
`0x8004c930`: if actor flags (`+0x5c`) bit `0x2` is set and Flik is within a per-object
radius, the motion goal swaps from the wander/path target to Flik's own live position.
Already proven by suppressing that bit on a live chasing spider and watching pursuit flip
from `+0.93` to `−0.89`.

Tested the archived note's literal claim first (`FUNC_8004DF18`) and abandoned it
immediately — `re_symbols.sym` already names that address `camera_follow_update`, not a
chaser function, matching a correction this project already made once before (the same
address was also wrongly claimed as Hopper's own actor slot, corrected earlier this
session). Instead, armed `accessLog` write-watches directly on `id=22`'s own live position
fields (X, Z) during the confirmed-pursuit window of
`Hopper_white_berry_death.movie.json`. Both writes (X at `0x8004cd64`, Z at `0x8004cdcc`,
every 2 frames) land inside `FUNC_8004C13C` — the mover-VM, not the camera function.
Hopper's own program pointer (`actor+0x70`) read `0x800778cc` at the sampled instant —
inside a long, previously unattributed block of `analysis/vm_programs.md` (past the last
named header, `redbug @ 0x80077690`), a generic wander loop shaped like every other
species' own simple program.

Checked `id=22`'s own flags bit `0x2` at 7 sampled frames spanning the confirmed-pursuit
window (movie-relative 10/50/100/150/200/250/300): **set at every single sample**,
correlating with distance oscillating 8,261–46,299 units as he closes to throwing range
and backs off — consistent with a ranged attacker's own approach-and-reposition pattern,
not a pure melee closer. Cross-checked against the earlier finale-trigger trace's own
flags reads near defeat (`0x5051`/`0x5050`): bit `0x2` reads **clear** there — his chase
gate disengages before the scripted bird-nest cinematic, a sensible design choice (combat
AI turned off for the cutscene).

**This also surfaced and fixed a stale project memory entry.** `enemy-ai-state-machine.md`
(a persistent memory file, not a repo doc) had the general chaser-driver question flagged
as an "OPEN residual" — but it had actually been resolved the same week it was flagged;
the `enemy_ai_programs.c` resolution was just never cross-linked back into that memory.
Corrected as part of this banking pass, along with a new dedicated `phase4-d20-hopper`
memory entry and the `MEMORY.md` index.

**Genuinely still open**: Hopper's own chase-radius scratch value (established elsewhere
as a per-program parameter, e.g. 1000 or 400 units for other species — not read for
`id=22` specifically); whether the gate is ever off during active, non-cutscene play, or
is simply always-on throughout any encounter (confirmed ON for 7/7 samples, not proven
ALWAYS on); Hopper's own full mover-VM program was not walked start-to-end or given a
species name in `vm_programs.md`; barrier/retreat behavior specifically (the gate
mechanism is now confirmed, but that's a different question from whether/how he
disengages or retreats).

## Three-section encounter structure — investigated, partially (2026-08-03)

Operator described three distinct areas and asked whether each was documented: an
opening encounter where hitting Hopper drains a UI health indicator; a platforming chase
where, once hit, Hopper retreats to patrol a separate area until Flik gets near "a gate";
and a mountain-climbing section. Honest answer at the time: none of it had been checked.
Operator confirmed the breakdown was accurate and said to start digging.

Reloaded `D20.movie.json` fresh (`/tmp/dsrepro-d20phases`, port 23610). Combined a coarse
screenshot survey (every ~1000-1500 frames from movie-relative 0 through ~15000) with
`accessLog` watches on Flik's health and `id=22`'s own hp/flags, plus a breakpoint at
`FUNC_8004A700`'s entry to catch damage-event callers.

**Section 1 (health drain) — confirmed, with a real nuance.** `id=22`'s own `+0x6e` field
DOES take real `-2` damage on a hit: caught the exact write at movie-relative frame 5914,
PC `0x800590e4` — inside `0x80058af8`, the already-Canon generic enemy hit-tail function
used campaign-wide (`contact_vs_actor_handler`). This contradicts this row's own earlier
"static across sessions" read for that field — which had only sampled two *unrelated*
snapshots, not a live combat sequence, so it was never a fair test. But 2 frames later
the field is RESTORED to its prior value via `0x800b418c` — inside the SAME
boss-combat-overlay merged region as the white-berry aim caller (`0x800b46d4`) already
found in an earlier pass, and suspiciously close to the archived note's own
Thumper-overlay callers (`0x800b4138`/`0x8009c024`) — a new lead that Hopper and Thumper
may share ONE combat-overlay blob. This exactly mirrors Thumper's own already-documented
pattern: the raw actor field takes generic damage, but the real bookkeeping (whatever a
UI bar would reflect, whatever determines an actual defeat) lives in the overlay, which
immediately reverses the generic write to prevent Hopper dying via the shared
regular-enemy pathway. Checked 2 screenshots at the exact hit moment (one shows a blue
berry marker directly on Hopper's body, confirming a landed throw) for a dedicated
on-screen Hopper health bar, matching Thumper's own documented "5 red segments" — found
none, but this is not exhaustive; only 2 frames were checked out of a fight involving
multiple hits. The 4 hits Flik took in this same window were traced via the
`FUNC_8004A700` breakpoint: 3 direct-contact (`0x8004B4A0`), 1 ranged white-berry
(`0x80058A48`) — a mix, not purely one damage type.

**Section 2 (patrol after a hit) — confirmed structurally, trigger not isolated.**
Immediately after the movie-relative-5914 hit, `id=22`'s chase gate (flags bit `0x2`)
reads false and stays false continuously through every sample from mf5920 to mf14500 —
roughly 8,600 frames, ~2.4 real minutes. He is not chasing, but not frozen either —
position moves substantially and repeatedly across a wide area, consistent with a
patrol/wander state. Confirmed back on by mf15000 (distance to Flik only 12,776 units) —
but that exact sample coincides with Flik's own on-screen death animation (part of this
same recording's already-documented "poor gameplay" death cycles), so it is NOT a clean,
isolated capture of a deliberate gate re-trigger. The literal "gate" condition — a level
trigger volume, a timer, a distance threshold, something else — was not isolated.

**Section 3 (mountain climb) — not investigated in that pass**, but closed the same
session. See below.

## Mountain climb confirmed — operator-annotated (2026-08-03)

Operator: *"I'm assuming we're safe to look into Section 3 now or is there a blocker?"*
No blocker — the fixture and technique were already proven out; the only friction is the
known large-jump client-timeout pattern, which doesn't stop progress since the emulator
instance itself survives and reconnecting works reliably. A short blind-sampling attempt
found the bird cutscene starting earlier than expected (see correction below) but no
distinct climbing section. Operator then supplied the exact window from memory: *"starts
around 11900, flik makes it to the top at around 14645."*

Fresh instance, sampled Flik's own position at 8 points across that window. His Y
coordinate changes **monotonically** — zero reversals at any sample — for a net change of
~338,000 units over ~2,745 frames (~46 real seconds). Elsewhere this session, ambient
wander/patrol position data oscillates back and forth; this doesn't — it's a genuine,
sustained elevation change. Screenshots confirm visually: the start (mf11900) looks like
the same walled-maze/log-obstacle terrain seen throughout the level; the midpoint
(mf13100) shows unambiguous stepped rock-ledge platforming with a visible drop to a lower
area in the background; the top (mf14645) shows Hopper visible again at a distance,
health at 2/5.

Checked `id=22`'s own state at the top: his chase gate (flags bit `0x2`) reads `false` —
consistent with the section-2 finding that it stays off for the whole surrounding
stretch — but his own elevation has independently converged to within ~8,000 units of
Flik's by this point. His own generic wander path, on the same mover-VM already
identified for him, also traverses the mountain's elevation change; he isn't chasing
Flik up it, but the terrain shapes his patrol too.

**A genuine correction, caught along the way.** This row had characterized the bird-nest
cutscene as starting "around movie-relative frame ~16100" — a coarse 1000-1500-frame
sampling grid that happened to land after its true start. Direct sampling this pass found
it actually begins around mf15700, immediately after Flik's own on-screen death/respawn
(lives 8→7) — his position is frozen bit-for-bit identical across mf15700-15850 (3
samples) while the camera shows Hopper first riding the bird's talons, then held in its
beak. The already-`accessLog`-confirmed scene_id write at mf16166 (the finale-trigger
section above) remains correct — it's a *later* event within this same broader cutscene,
not the cutscene's own start.

**All three of the operator's named sections are now structurally confirmed and located**
in `movies/Phase4/Interpreter/D20.movie.json`: section 1 (health drain, mf~1669-5914),
section 2 (post-hit patrol, mf~5920-14500 — the climb sits *inside* this stretch, not
strictly after it), section 3 (mountain climb, mf11900-14645), leading into the bird-nest
cutscene (mf~15700-16300+) and level-complete (mf~16700).

## "The gate" is literal, and the real hp-drain arc was missed on the first pass (2026-08-03)

Operator supplied three more precise annotations from memory: *"in the first area, 4702
lowers the UI hopper health which makes him run. Around frame 4888 is when he knocks down
the first wooden gate. Around 11825 is when he knocks down the SECOND wooden barrier in
the second area."* This reframed "the gate" entirely — not a Flik-proximity trigger as
the section-2 writeup above had assumed, but Hopper HIMSELF physically breaking through
scripted wooden barriers as part of his own flee path.

**Methodology fix.** The earlier `PHASE_STRUCTURE_INVESTIGATED` pass had armed its
`accessLog` watches on `id=22`'s hp/flags starting around movie-relative frame ~5549 —
already past frame 4702, so it structurally could not have seen anything before that
point. This pass reloaded `D20.movie.json` fresh (`/tmp/dsrepro-d20gates`, port 23625) and
armed the same watches from movie-relative frame 0.

**The real hp arc.** Hopper's hp initializes to 30, not the 20 this row had assumed from
comparing two unrelated snapshots (which were actually catching him at two different
points along the SAME post-damage floor, not two independent baselines). The
initialization write lands at PC `0x80049ca0`, movie-relative frame ~1033-1035. A rapid
burst of roughly 9 hits lands between mf4245 and mf4745 (500 frames, ~8.3 real seconds),
each the same already-Canon `-2` via the generic hit-tail PC `0x800590e4`, driving hp down
to a floor around 18-20. Once that floor is reached, the overlay's own restore mechanism
takes over: a SECOND restore call site was found this pass, `0x800b433c`, alongside the
already-known `0x800b418c` — the two alternate, clamping hp back up near the floor after
most (not all) further hits. The operator's named mf4702 lands exactly inside this burst,
right where hp crosses that floor for the first time — which is also, per the earlier
aggro/chase pass, almost exactly where the chase gate (flags bit `0x2`) was already
observed to go false. Crossing the floor reads as the actual trigger for both the flee
behavior and the chase-gate disengage, not an arbitrary timer or scripted cue.

Checked screenshots at mf4702 and mf4710 specifically for the operator-named "UI hopper
health" — found only Flik's own 5-segment health bar and a purple/magenta hit-impact
flash on Hopper's own body, not a distinct separate Hopper health-bar UI element. This is
now the SECOND pass to check for this (5 frames total across both passes) without finding
it. Flagged as a genuine, unresolved discrepancy with the operator's own description
rather than claimed as confirmed either way.

**Both wooden barriers confirmed as real, destructible, scripted geometry.** Screenshots
at mf4888 and mf11825 show a visually identical X-shaped wooden log barrier structure,
with Hopper's own model visibly tangled in/breaking through it across the sampled frames
at each location. Both are confirmed genuinely destroyed afterward: checked at mf4900
(first) and mf12100 (second) — the structure is completely gone at both. The second
barrier sits immediately before the already-confirmed mf11900 mountain-climb start — it is
the literal transition marker into section 3, not a separate mechanism. State at both
break events: hp already at the post-burst floor (20), chase gate already false in both
cases (consistent with the flee state established at mf4702 persisting through both
barrier events).

Not traced this pass: the exact opcode/instruction responsible for spawning or despawning
the barrier geometry itself. Best current explanation, hedged and not confirmed via
disassembly, is a scripted waypoint event on Hopper's own mover-VM flee path — the shared
VM ISA already includes path-following opcodes (`seek_path_endpoint`, `path_next_waypoint`,
`park_path`) that would fit a "flee to a scripted point, break through an obstacle,
continue" pattern.

## The real health bar found, correcting the "not found" read from the same day (2026-08-03)

Operator posted a screenshot of the actual on-screen bar (top-left, 5 red segments) with:
*"It's the 5 bars up here. Something is triggering this to lower down."* This falsifies
both this row's own just-prior claim (two passes, 5 frames checked, "not found") and the
much older archived note's claim that Hopper has no HP bar at all ("Defeat is scripted
phase/trigger progression, not HP-depletion").

**Found by reading source, not guessing addresses.** `src_re/hud_800526f4.c` — already
Canon, already-decompiled `FUNC_800526F4` HUD-draw routine — documents in
`draw_other_scene_panels()`: *"Scenes 2/11/13/14/15 select the raw progress globals above
and render a common five-segment tile-0x75 meter."* `G_HUD_SCENE15_PROGRESS = 0x800b4ba8`
is already named in the same file's macro block for scene 15 — Hopper's own
canyon-showdown scene.

**A methodology bug caught and fixed en route.** `movie.startPlayback` defaults
`load_start_state` to **false**. An early poll-only check without that flag silently
replayed the movie's inputs onto boot-state garbage (`scene_id` read 0 or 12, `id=22`
absent from the actor table) instead of the real fight — confusing at first, since the
inputs themselves were still being faithfully replayed, just against the wrong starting
state. Passing `load_start_state:true` fixed it immediately (`reproducible:true`,
`scene_id=15`, `id=22` present, `hp=30` matching expectations).

**Full write trace.** `accessLog` armed on `0x800b4ba8` from movie-relative frame 0,
advanced through to the finale window: 20/20 write events captured, no truncation.
- mf1170, PC `0x800b3b04`: init 0→30.
- mf4697, PC `0x800b4164`: 30→28 — within 5 frames of the operator's own named mf4702,
  via a *distinct* first-hit handler.
- mf5916 / 7170 / 9644 / 11178 / 11610 / 12598 / 13262 / 14170 / 14772, all PC
  `0x800b41c8`: nine more `-2` decrements (28→...→10), a *shared* regular-hit handler,
  spaced roughly every 1000–1500 frames across the whole remaining fight — not clustered
  in a single burst the way the decoy `actor+0x6e` field was.
- mf14836 / 14884 / 14962 / 15232 / 15280 / 15332 / 15386 / 15438, all PC `0x800b4270`:
  eight `-1` decrements (10→...→2), a *third, different* handler, in a tight late-fight
  cluster.
- mf15490, PC `0x800b428c`: final write, 2→0 — immediately before the already-confirmed
  bird-cutscene onset (~mf15700).

**Segment count = `ceil(value/6)`**, visually confirmed at three independent, widely
separated points: value 30 and 28 (several screenshots, mf4200–mf5914) both show 5/5 lit;
value 24 (mf7200) shows exactly 4/5 (the 5th segment visibly dark); value 2 (mf15450, with
the bird's wing already entering frame for the cutscene) shows exactly 1/5. No
counter-examples across any sampled frame.

**This corrects, not merely supplements, the "real hp arc" finding from earlier the same
day.** `actor+0x6e` (init 30, burst-drained to a floor ~18–20, restored by the overlay) is
real and accurately reported, but it is a **secondary/decoy field** — not what the bar
shows, not what gates defeat. The true, unclamped, on-screen defeat counter is
`0x800b4ba8`, which keeps draining long after `actor+0x6e` has already floored (still 28
at mf5914, when the decoy field has been pinned at 20 since mf4700). The mf4702
flee-trigger correlation still holds — both fields react to the same hit-burst — but the
mechanism is now precise instead of inferred.

**Closes, for Hopper, the exact residual the archived note left open for Thumper**: *"HP
field + per-hit delta + N-hits-to-defeat — the bar visibly depletes... but the counter is
in the overlay, not isolated."* It also hands Thumper's own row (other agents' active
work this session, not touched here) a ready-made, unverified lead: the same source file
documents the identical mechanism for scene 14 (`G_HUD_SCENE14_REMAINING @ 0x800b4cc8`),
and Bug Bar's player-facing stage 9 is already established to run as scene 14.

**An unrelated, pre-existing Canon inconsistency surfaced while checking candidate health
addresses** — not created by this pass, and out of scope to resolve here:
`MEM_800A6500_Player_state_800A6500.md` calls `0x800A6594` Flik's own "true health," while
`src_re/player_health.c` (RCG-021) calls the same address the health-leaf mercy-drop
counter and names `0x800A7E2A` (full = 7) as the real displayed health. `0x800A7E2A` was
independently confirmed this pass to read wildly inconsistent values frame-to-frame during
live gameplay (3, 3, 3, 5, 1, 7, 1, 3, 5, 7, 2, 5, 3, 4, 6 across one sweep), consistent
with `player_health.c`'s own documented caveat that it is HUD-animated and unreliable to
poll mid-motion. Flagged for whoever owns Flik's own health-economy row.

## Defeat-trigger caller and overlay identity closed, gate-break opcode narrowed (2026-08-03)

Operator: *"go for those three items in well-scoped [way]"* — the three residuals named in
the prior status report. Two close cleanly; the third makes real progress without landing
the specific answer.

**Defeat-trigger caller — CLOSED.** Set an execute breakpoint directly at
`scene_setup_and_load`'s own entry (`0x8005038c`) rather than starting from the counter
write, on a fresh Interpreter-mode instance replaying `D20.movie.json`. Large single jumps
proved unreliable for reading a breakpoint's exact register state (the core appears to
auto-resume past a hit before a subsequent large `advanceToFrame` call returns) — small
20-frame steps, polling `hit_count` after each, caught it cleanly: hit at movie-relative
frame 16150, `pc=0x8005038c`, `ra=0x800502d8`. `functionBounds` on that return address
resolves to `0x800502c4-0x80050388` (confidence exact) — exactly
`fmv_sequence_completion_check`, already this row's own "strongest candidate" from the
earlier finale-trigger pass. Disassembly of the call site confirms it precisely:
`addiu sp,sp,-24 / addiu a0,zero,4 / sw ra,0x10(sp) / jal 0x8005038c / addiu a1,zero,128`
(delay slot) — matching the captured register state (`a0=4, a1=128`) exactly. Confirmed,
not merely inferred.

**Overlay file identity — CLOSED.** The project already has a working cold-boot lever,
`tools/trace_warp_landing.py`: replay the from-boot `flik_to_level01_stall.mv.movie.json`,
fast-forward through the front-end, then poke the scene-select table
(`0x80077FA0`, 8 entries) *before* the game's own scene-init latches it, diverting the
natural boot to an arbitrary target scene. Its own docstring names index 1 as the lever
("LEVEL01 = idx1"); a first attempt sustained-poking index 1 to 15 through the whole latch
window — confirmed via direct table reads to have genuinely held — still landed on
`scene_id=17`, the table's own untouched index-0 value. A second attempt poking **index 0**
instead correctly landed `scene_id=15, stage=15` — this specific boot movie's own natural
selection reads table[0], not table[1], contradicting the tool's generic docstring claim
(validated there only for targets 2/3/6, not this exact movie/scene combination) — a live,
empirical correction worth carrying forward. The player object itself never spawned from
this raw divert (position stayed at the origin through 300+ more frames), but that didn't
block the goal: `transferLog` was armed the moment of the poke and captured the level's own
CD-ROM DMA traffic regardless. `transferLog.resolve` on the already-known overlay addresses
(hp-restore sites, white-berry spawn caller, the health-counter writer PCs) all resolve
unambiguously to **`LEVEL05/LEVEL1.DAT`**, uncompressed, with an exactly-linear
RAM-to-file-offset mapping holding across every address checked (every address delta
matched the corresponding file-offset delta exactly). A few addresses right at the region's
start resolve *ambiguously* — one candidate is an earlier, unrelated `LEVEL00/LEVEL.RAW`
load sharing that same fixed RAM slot, ordinary PS1-style overlay-address reuse, not a real
conflict. Addresses further out resolve instead to a *different* file entirely —
`LEVEL05/LEVEL5C.VB`, an audio bank — meaning the 121,200-byte "merged, low-confidence"
region `functionBounds` flagged earlier this session was never one coherent function: code
early, the same RAM reused later for streamed audio, exactly why the static heuristic scan
produced an implausible size. **This refutes the "Hopper and Thumper share one overlay"
hypothesis** raised in an earlier pass — Thumper's own overlay is the separate
`LEVEL04/LEVEL1.BIN`; the two merely share a per-level naming convention
(`LEVEL1.{DAT,BIN}`, a "slot 1" combat overlay per boss level) and a similar fixed load
address, the ordinary overlay pattern, not one shared file.

**Gate-break opcode — NOT closed, genuine progress instead.** A separate, already-closed
row (`E07_event_vm`, see `EXP_2026-08-02_phase4_e07_bounded_exhaustion.md`) had already
statically mapped the mover-VM's op12 native-CALL sub-table: `LEVEL05-1 slot 5 / program
28` maps to overlay predicate `0x800B3BD4`, with exactly one active record campaign-wide —
matching Hopper's own singular chunk-31 instance exactly. Set an execute breakpoint there
and traced live from mf4700 through mf11900, spanning both wooden-gate events. The
predicate first fires at movie-relative frame 4700-4701 — within 1-2 frames of the
operator's own named mf4702, and the same window as the already-confirmed first real-hp-
counter decrement (mf4697) — with `a0=a1=0x800a0224`, Hopper's own actor pointer.
Disassembly of the immediate caller (inside the mover-VM interpreter itself,
`0x8004c340-0x8004c38c`) shows a per-actor wait-counter handler: increments actor `+0x5e`
(refining E07's own static wording — it called the compared value a "resident halfword,"
but it's actually actor-*relative*, since `0x800a0224+0x5e = 0x800A0282` exactly for
Hopper's specific instance), compares the incremented value against a per-program
threshold operand, and sets the branch flag `s3` when the threshold is crossed. But
continuing the trace to mf11900 found this same predicate fires **hundreds more times**
throughout the whole patrol phase — every 6-30 frames, often in dense bursts — not uniquely
at either gate. It's a general, recurring "wait N ticks, check a condition" pattern
embedded in Hopper's own ordinary patrol loop, not a rare, gate-specific trigger. **Ruled
out as the answer, not ruled in** — the real gate-break instruction is still unidentified.
One anomaly surfaced but not chased given time: the last call sampled before mf11900
(mf11898) showed a *different* actor pointer, `0x800a0644`, suggesting the same predicate
may also fire for another actor near the second gate.

A methodology bug of my own cost real time mid-investigation: an early attempt to sweep
predicate hits from mf4701 toward the second gate looped forever at the same frame,
because clearing and re-adding a breakpoint while the core sits paused *at* that exact
instruction just re-triggers it immediately on the next advance — the fix was to
temporarily remove the breakpoint, step a few frames past it, then re-add it before
continuing.

Full detail: `analysis/phase4_d20_hopper.json`'s
`DEFEAT_CALLER_OVERLAY_AND_GATE_OPCODE_2026-08-03`.

## Residuals

The actual gate-break trigger instruction (a related overlay predicate was found and ruled
OUT, not ruled in — one unchased anomaly: the same predicate's last sampled call before
mf11900 showed a different actor pointer, `0x800a0644`); the LATER chase-gate
re-engagement trigger near mf15000 (still confounded by an unrelated player-death event);
whether each of the 20 accessLog-observed `0x800b4ba8` decrements corresponds 1:1 to a
single hit or to something coarser (a per-encounter event) — not disambiguated; why the
decrement amount changes from `-2` to `-1` partway through the fight (plausibly a phase
transition matching the archived note's own mode-flag model, not confirmed); the overlay's
own precise byte extent within `LEVEL05/LEVEL1.DAT` (bounded to roughly
`0x800b3c04-0x800b5000`ish, not pinned tighter — a gap in transfer coverage at `0x800b6000`
blocked a cleaner boundary); the exact aim/cooldown logic inside that now-identified
overlay; whether the mountain climb has its own scripted/assisted mechanic beyond the
confirmed elevation change; Hopper's own chase-radius value; Hopper's own mover-VM program
not walked/named; ending transition past level-complete; campaign breadth for stage 13's
own content (Atta/stage-14 confirmed OUT of scope); source closure; cross-system audio;
the pre-existing `0x800A6594` Canon inconsistency (flagged, not this row's to resolve).

**Assessment**: the core combat/chase/defeat MECHANISM is judged BOUNDED/substantially
exhausted after this nine-pass session. Of the three specific follow-ups requested, two
closed cleanly with instruction- and file-level confirmation (the defeat-trigger caller is
`fmv_sequence_completion_check`; the boss-combat overlay is `LEVEL05/LEVEL1.DAT`, refuting
the earlier Thumper-sharing hypothesis), and the third made genuine, well-evidenced
progress — a real overlay mechanism was found, disassembled, and an existing row's own
static description was refined — without reaching the specific gate-break trigger, reported
honestly as partial rather than claimed solved. The operator's own 3-section encounter
STRUCTURE remains fully confirmed and located. The remaining open items (the actual
gate-break instruction, the later re-engagement trigger, the overlay's exact byte extent,
the phase-transition question) are well-scoped last-mile questions, not open questions
about whether the operator's described mechanics exist.
