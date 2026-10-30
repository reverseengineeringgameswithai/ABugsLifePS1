---
type: experiment
status: complete
date: 2026-08-02
system: enemy AI / D15 daddy long legs
phase: 4
artifacts:
  - analysis/phase4_d15_daddy_long_legs.json
  - ObsidianVault/Canon/Systems/SYS_enemy_ai.md
---

# Phase 4 D15 daddy long legs — identity, no-strike, combat, aggro-negative

## Question

D15_daddy_long_legs was fully unresolved: "Locate daddy-long-legs actor type in chunk-31
rosters" was the row's own next-step, actor id unknown going in. Picked as the next row
after D11/D12's mite+grub work reached a documented, deliberate stopping point. A
purpose-recorded fixture already existed (`D15_daddy_long_legs_contact_kill.movie.json`,
416 frames, format v3) but had never been indexed — the registry still showed
`fixture_have: []`.

## Identity: not a misattribution this time, just an internal-name gap

The fixture's two live actors were `id=6` (hp=8, untouched the whole recording) and `id=17`
(hp=4, the actual kill target — confirmed by tracing the movie's own `square` throw windows
against both actors' hp). Both IDs were already independently named elsewhere: `id=6` is
Horsefly (`0x0f06`, D08_flies' own subject), `id=17` is "huge_spider" (`0x0b11`, listed as a
D10_spiders fixture but never characterized live). Neither is an obviously-named "daddy long
legs" by internal census name — the same situation that turned out to be a genuine
misattribution twice earlier the same day (D11's old fixtures).

Captured a live frame near `id=17`: a distinctive silhouette with extremely long, thin,
spindly red legs radiating outward from a small green/purple body, partially visible behind
a cardboard-box structure in a night-time "city" area. Asked the operator to confirm before
treating it as fresh D15 evidence — this time it checked out. Operator, directly:
*"'huge_spider' is daddy long legs, fyi."*

Type-word cross-checked live via the same runtime backlink method (`+0x80`) already used for
worm/mite: reads `0x0b11`, matching the archived `Enemy_spawn_architecture.md` table exactly
(low byte `0x11` = 17, the established rule).

## No strike mechanic, confirmed statically for free

`analysis/vm_programs.md` already has a dedicated labeled section,
`## huge_spider @ 0x80077674`: a plain wander loop (`set_byte_params → anim_clip_load →
wait_random → random_dir_step → park_seek → jump_back → park_end`) — no `player_proximity`
opcode, no `call_native`. This directly answers the row's own named scope item, "web
projectile, range behavior": there is no such mechanic in this creature's own mover-VM
script. (A purely decorative web *object*, as opposed to a live-actor attack, was not ruled
out — not investigated this pass.)

## Combat, live-traced

Berry marker read live at f280: value `1` — BLUE class. Timeline: gate (`0x800a6596`)
activates f286, connects (hp 4→2) f318; gate activates f328, connects (hp 2→999, the
delayed-destroy sentinel shared across species) f352; removed from the live table at
**exactly f400**. Damage is `-2`/hit, matching the already-established generic hit-tail
blue/homing amount used for worm and others — not a species-specific override.

## Aggro/chase — first pass CONFIRMED NEGATIVE, then RETRACTED after operator correction

Same method proven for mite/grub earlier the same day: watched flags (`+0x5c`) and physical
position (`+0x04/08/0c`) against Flik across the first hit and for ~6 real seconds via
`debugger.resume` polling.

**Flags stayed completely unchanged** at `0x4103` through the hit (checked at 1-frame
resolution across f314-324, zero transition) — unlike *every other species tested this
session*. Position showed no directed movement either: 53359 units from Flik just before
the second hit, 53608 units several seconds later. Banked as "CONFIRMED NEGATIVE."

**This was wrong to generalize, and the operator caught it**: *"surely it has aggro since it
shoots a web?"* The test never brought Flik anywhere near attack range — both hits in the
only fixture used were thrown-berry hits from 53000+ units away. A "no reaction at that
distance" result cannot rule out an attack the creature never got a chance to attempt.

**Follow-up, inconclusive.** The operator supplied a save state from their own DuckStation
savestates directory (`~/.local/share/duckstation/savestates/savestate_1.sav`) — copied
(not moved) into `movies/Phase4/D15_daddy_long_legs_web_attack.sav` — described as showing
"Flik in the vicinity of the daddy long legs. Shortly after, the spider turns to Flik and
throws a web at him." This save is `scene_id=1` (chronological Level 2), a genuinely
**different level** from the combat fixture's `scene_id=5` (Level 8) — new campaign-breadth
information on its own (this species spawns in at least 2 levels).

Of 5 live actors in that save, only `id=14` has an active proximity-check opcode in its own
program (`player_proximity[1200]`, inside `## mosquito @ 0x800775e4` in `vm_programs.md`).
Careful, incremental position-based approaches — keeping Flik's own Y coordinate rather than
the target's, after one earlier teleport attempt sent Flik's Y exploding through unstreamed
floor geometry (a standing project hazard from blind position pokes, not creature behavior)
— closed the distance to `id=14` down to ~9000-20000 units without ever triggering an
attack; the actor's own wander cycle carried it away again each time. Whether `id=14` is
even the correct target actor for "daddy long legs" was not resolved this pass. The operator
ended the thread here — *"daddylonglegs in ABL is fine"* — rather than continue guessing.

**Net effect at the time**: the CONFIRMED NEGATIVE conclusion is retracted. What survives is
narrower: no reaction was observed in one specific far-range fixture, and no attack opcode
exists in one specific program address — neither generalizes to "no attack mechanism."

## The web attack, confirmed live

The operator loaded the follow-up save into a running isolated instance, watched it
directly, and recorded a proper movie of the encounter:
`movies/Phase4/Interpreter/DaddyLongLegs.movie.json` (1448 frames, format v4). This lands in
`scene_id=5` — the SAME scene as the original combat fixture, confirming beyond doubt this
is `id=17`.

Live-traced Flik's health, the target's hp/flags, and their XZ distance across the whole
movie. Flik's health drops in three separate steps while the target's own hp stays at 4
(undamaged) the entire time:

| Hit | Frame | Distance |
|---|---|---|
| 1 (health 4→3) | f312 | 73,286 units |
| 2 (health 3→2) | f604 | 48,405 units |
| 3 (health 2→1, target flags gain bit `0x1000`) | f798 | 14,245 units |

These distances are one to two orders of magnitude beyond any plausible contact range —
unambiguous evidence of a genuine ranged attack. It doesn't fire on a tight radius or a tight
timer: hits land 190-290 frames apart while distance to Flik swings between ~14,000 and
~77,000 units over that span, unlike worm's fixed 700/1200-unit proximity windows.

Flik then counter-attacks: gate `0x800a6596` reads `3` at f1280 (multiple berries in flight
simultaneously), first hit lands (hp 4→2) f1280-1282; second hit (hp 2→999) f1340-1342;
removed from the live table at exactly f1390 — defeated.

**This fully reverses the AGGRO_2026-08-02 finding**, not just leaves it retracted. The
species has a real, confirmed ranged web attack. The operator's original correction —
*"surely it has aggro since it shoots a web?"* — was exactly right.

Still open about the mechanism: the exact trigger (timer vs. proximity vs. a hard-coded
per-id check, paralleling how worm's real strike lives in a `call_native` outside its simple
wander program — not traced to an instruction here, only inferred behaviorally); whether the
web is a directly observable spawned/tracked object; why flags bit `0x1000` appears only at
the third hit, not the first two.

## Producer chain traced, including a self-caught correction

Per the operator's "keep drilling down until you deem it substantially exhausted," the
full chain was traced live in an Interpreter-mode isolated instance replaying
`movies/Phase4/Interpreter/DaddyLongLegs.movie.json`.

**Damage side** closes against already-Canon code: the health-decrement write
(`0x8004a888`, inside `FUNC_8004A700`) is called from `0x80058A48`, inside the
already-decompiled `FUNC_800586B0`/`contact_walker` (`src_re/contact_walker_800586b0.c`),
which dispatches on the contact-pool record's `action_id=118` — a value that file's own
prior comment had already flagged as aliasing to the documented `WALKER_CASE_UNK_52`
case, just never connected to "this is the D15 web attack" before this pass. The record
was confirmed live as a genuinely moving, tracked object: its distance to Flik closes
across consecutive frames immediately before each hit registers.

**A first spawn-side lead was wrong, and the correction matters more than the lead.** A
breakpoint at the primary contact allocator's entry, combined with a `$ra` trace timed
near the right frames, pointed at a call inside `FUNC_800563D4`/`actor_skinned_update`
(`ctorType=49`). Before banking this, a direct memory read of the constructor metadata
table's row 49 showed `action_id=1`, not 118 — contradicting the claim. That call site is
real (disassembled and documented on its own Canon page as a ruled-out D15 lead, so a
future pass doesn't re-chase it), but it produces something else. Nothing about this false
lead had been committed to git before the correction was made.

**The real chain**: the actual write (`0x8005a1d8`) sits inside a separate sibling
allocator (`0x8005A0E0`) — already partially Canon as `FUNC_80059E44`'s own "explicit
constructor" variant, and also used, completely unrelated to D15, by the berry-throw
system. Its caller is `0x8004A2B0` — a 380-byte function that already had a static name
from prior analysis (`aimed_object_spawn_sfx`, `analysis/naming/u2_batch04.json`,
rationale "spawns a contact object with computed heading + sound") but no Canon page and
no live-confirmed gameplay meaning until now. It aims at Flik via an atan2 helper, runs a
randomized `[40,103]`-frame per-candidate attack cooldown, spawns the web via a FIXED
metadata pointer (`0x80079da4`, read live: `action_id=118`, `active_type=60`), and
immediately fires an SFX call with id `25` — very likely the web's own sound, a free
answer to the row's audio gap.

**Dispatch is an optional per-species callback, not a hard-coded check.** The function is
reached only via an indirect `jalr`, matching a pre-existing static census
(`analysis/phase3_fn_ptr_fields.json`): `actor_record+0x7C` is a 9-handler
function-pointer field, 1286 live instances censused, 60.8% hit rate.
`aimed_object_spawn_sfx` accounts for 68 of them; `mosquito_species_callback` — the
D07_mosquitoes row's own independently-confirmed callback, found by a different agent the
same session — is a sibling value in the exact same slot. This is the same optional
per-species-callback architecture as D07's own finding, cross-validating both rows. The
one link not closed: reading id=17's own live `+0x7C` field to directly confirm it equals
`0x8004A2B0`. Two attempts hit unexplained movie-replay non-determinism on reload in the
long-lived isolated instance (a clean breakpoint setup that fired reliably on the first
run produced zero hits on a fresh reload) — a tooling artifact, not chased further.

Full trace, including the ruled-out lead: `analysis/phase4_d15_daddy_long_legs.json`'s
`PRODUCER_CHAIN_TRACED_2026-08-02`. New Canon page:
`ObsidianVault/Canon/Functions/FUNC_8004A2B0_aimed_object_spawn_sfx.md`.

## Callback confirmed live (2026-08-03)

Per the operator's "go for d15," picked back up to close the one remaining well-scoped
item named in this note's own Residuals: whether `id=17`'s own live actor record
actually carries `+0x7C = 0x8004A2B0`. The prior two attempts were blocked by
unexplained movie-replay non-determinism in a long-lived, many-times-reloaded isolated
instance.

A **fresh** isolated instance (`/tmp/dsrepro-d15-callback-20260803`, port `23590`,
launched via `tools/launch_repro_playback.sh --execution-mode Interpreter`, confirmed
`ExecutionMode=Interpreter` in the written `settings.ini`), loaded once
(`movie.load` + `movie.startPlayback(load_start_state:true)`, never reloaded), replaying
the same `movies/Phase4/Interpreter/DaddyLongLegs.movie.json`. At each of 6 sampled
frames spanning the whole 1448-frame movie (350/500/700/900/1100/1300), scanned the
damageable object pointer table (`0x80090748`, 64 slots), dereferenced each live
pointer, and read `id`/`hp`/`flags`/`+0x7C` from the matching record.

**Result: `+0x7C = 0x8004A2B0` at every one of the 6 samples, zero variation.** The
record itself stays at the same address (`0x800a0ae8`, matching the earlier combat
trace) throughout, even though its slot INDEX in the pointer table shifts (2→1) as the
table compacts around other actors. `hp` and `flags` at each sample independently
matched the already-documented combat timeline (hp 4→2 bracketing the f1280 counter-hit;
flags `0x4103`→`0x5103` bracketing the f798 bit-`0x1000` event) — cross-validation that
this is genuinely the same `id=17` record, not a coincidental match.

This closes the row's last well-scoped residual. The earlier non-determinism reads as a
tooling artifact of a long-lived instance carrying many prior reloads, not a finding
about the game — a single fresh session reproduced cleanly on the first attempt.

Updated: `analysis/phase4_d15_daddy_long_legs.json` (`CALLBACK_CONFIRMED_LIVE_2026-08-03`),
`ObsidianVault/Canon/Functions/FUNC_8004A2B0_aimed_object_spawn_sfx.md`,
`ObsidianVault/Canon/Systems/SYS_enemy_ai.md`, `analysis/mechanics_baseline.yaml`.

## Reproduction

```bash
python3 -m pytest -q tests/test_phase4_d15_daddy_long_legs.py
tools/launch_repro_playback.sh --config-dir /tmp/dsrepro-d15 --port 23555 \
  --token debugger-1000 --disc "Disney-Pixar A Bug's Life (v1.0).cue"
```

The fixture is format v3 (CachedInterpreter) — the default launcher execution mode was used
to match, per the D17-established launcher/settings.ini gotcha. All live reads were
`movie.advanceToFrame` sampling of the target's own record, cross-verified once via real
`debugger.resume` polling for the aggro test.

## Residuals

CLOSED 2026-08-03: whether id=17's own live actor record actually carries the
hypothesized `+0x7C = 0x8004A2B0` callback — see "Callback confirmed live" above.

The outer per-tick scheduler that fills `aimed_object_spawn_sfx`'s scratch argument; why
flags bit `0x1000` appears only at the third hit; campaign breadth (confirmed at least 2
levels — `scene_id=5` and `scene_id=1` — a static exhaustive scan across all 11 level
directories was attempted and abandoned: no per-level actor-chunk-index map exists in this
project, and a naive heuristic scan matched `0x11111111` filler bytes in unrelated
texture/model chunks, not real actor tables); respawn behavior (neither fixture runs long
enough post-kill to observe a cycle); a full berry-class immunity sweep (only blue was
tested); mine interaction; the id=6 Horsefly and id=19 actors present but untouched
(assumed unrelated, other rows' scope); source closure for `0x8004A2B0` and the sibling
allocator `0x8005A0E0` (the damage/walker side already has source,
`src_re/contact_walker_800586b0.c`); independent by-ear confirmation that SFX id 25 is
really the web's own sound.
