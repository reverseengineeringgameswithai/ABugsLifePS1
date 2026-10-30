---
kind: experiment
id: EXP_2026-07-16_phase4_lives_gameover_continue
date: 2026-07-16
phase: 4
row: C16_lives_gameover
status: reproduced_active_partial
source_state: original_game
evidence: [analysis/phase4_lives_gameover.json, analysis/phase4_lives_death_breadth.json, analysis/phase4_checkpoint_respawn.json, analysis/phase4_c16_frontend_card.json, analysis/phase4_c16_boss_death.json, analysis/phase4_c16_bonus_death.json, analysis/phase4_c16_thumper_death.json, analysis/phase4_c16_thud_boulder_death.json]
---

# Phase 4 C16 — lives, game over, ordinary respawn, and title restart

## Question

Does the existing historically named `C16_gameover_continue` recording
reproduce a pristine final-life transition, and what frontend boundary does
its fourth Start actually select?

## Fixture admission and isolation

Both Phase4 and broader movie trees were recursively inventoried before the
campaign was selected. The movie and state were admitted through
`analysis/phase0_2_knowledge_closure.yaml` and centrally pinned as external,
operator-owned bytes:

- movie SHA-256 `39fa618a…bf`, 2,739,616 bytes, `pristine_serial`;
- state SHA-256 `e9c7a3b6…1592`, 2,052,577 bytes, `pristine`.

The state was inspected before load: format 84, serial `SCUS-94288`, and its
embedded media path resolved to the hash-pinned pristine retail CUE. Replay ran
in a newly created `/tmp` config on a dedicated loopback port/token. The
generator stopped only the PID owned by that config.

## Method

The 4,006-frame v3 movie starts in Bug Bar with true health 1 and lives 0. Its
input consists of movement at frames 40–121 and four later Start bursts. Four
branches were reproduced:

1. natural movie;
2. the same movie with only movement frames 40–121 neutral;
3. a transient state whose two-megabyte main-RAM image differs only at
   `0x800A65A0`, lives 0 to 1;
4. the natural movie with only fourth-Start frames 3663–3669 removed.

Transient save/movie derivatives stayed under `/tmp` and were deleted. Fixed
behavioral points used `movie.traceToFrame` with passive cached-interpreter
coverage; control and instrumented RAM/register/cycle/frame signatures had to
match. Separate `accessLog` runs forced the interpreter and were retained only
for instruction/old/new writer attribution, not fixed-frame timing.

## Observation

- Natural frame 400: scene 9, health -1, lives 0, master state 2. Damage PC
  `0x8004A888` and final-life scene-flow PCs `0x800500BC`/`0x800500D4`
  execute; the ordinary-respawn call `0x800500F4` does not.
- Neutral frame 400: scene 9, health 1, lives 0, master state 0, and zero hits
  in `0x8004A700..0x8004AA34`.
- Lives-one frame 400: scene 9, health 4, lives 0, master state 0. Coverage
  includes `0x8005B30C` and `0x8005B348`. Writer attribution records health
  `0→-1`, health `-1→4`, and lives `1→0` at those exact resident stores.
- Natural and fourth-Start-removed branches have identical full-RAM/register
  signatures at movie frame 3662. By frame 3700 natural lives are 5 and the
  control remains 0. The sole natural write is `sb v0,0x65a0(at)` at
  `0x80055550`, old 0/new 5. At frame 4006 the split remains 5 versus 0.

## Interpretation and causal confirmation

Observation: lives zero is playable, final death selects game over, a one-byte
nonzero control selects ordinary respawn, and fourth Start causes a five-life
scene-config write.

Inference at the first retained pass: the resident lives reader selects
final-life game over versus ordinary respawn; the fourth Start was provisionally
described as a Continue action applying scene configuration byte 5. Iteration 15
below disproves that frontend label while retaining the exact native write.

Causal confirmation: the controls change exactly one RAM byte, 82 movement
samples, or seven Start samples. Every retained fixed-frame coverage replay is
cycle-neutral against its own uninstrumented run, and the decisive writer words
are independently read from the pristine executable.

## Failed or bounded hypotheses

- A filename or serial string was not accepted as media proof.
- Removing any of the first three Start bursts also prevented progress within
  the 4,006-frame horizon; that did not identify a frontend choice. Only the
  fourth-burst comparison preserved exact equality immediately before its input.
- A first access-log attempt sampled ordinary respawn at movie frame 400. Since
  access logging forces the interpreter and changed the timing of that
  fixed-frame path, its frame result was rejected; writer attribution was
  collected by continuing until the native stores executed, while behavioral
  timing remained sourced from cycle-neutral traces.
- One contact-death path does not establish checkpoint coupling, every death
  class, frontend/card policy, or all-stage breadth.

No MOD-private hook, cave, state, or intended behavior was introduced, so there
is no Mods note for this experiment.

## Iteration-10 death-class join

The separately retained C15 experiment reuses the existing LEVEL02 pit pair.
Natural input changes health/lives `3/5` to `4/4`; neutralizing only frames
57–87 prevents respawn. It therefore adds a pit class and second stage to C16's
breadth. The same experiment rejects a simple stable safe-anchor selection for
that path, so checkpoint/safe-position ownership is not promoted here. See
[[EXP_2026-07-16_phase4_safe_respawn_anchor]].

## Iteration-12 safe-anchor consumption join

The C15 experiment reused this campaign's same Bug Bar movie/state pair and the
one-byte lives-1 derivative. At fatal source frame 350, same-code branches
differ only by safe X `+4096`; at the first completed respawn on source frame
355, live/safe X differs by exactly `+4096`, while Y/Z, scene and health/lives
`4/0` remain equal. Exact resident safe loads, live stores, health restore and
lives decrement execute under identical bounded branch coverage. This closes
the ordinary contact safe-anchor-consumption question only; scripted/special
deaths, frontend/card effects and multi-stage breadth remain open. See
[[EXP_2026-07-16_phase4_safe_respawn_anchor]].

## Iteration-13 multi-scene natural death-law join

The mandatory recursive census again found 110 Phase-4 files and 147 files in
the broader movie tree. The eight already pinned E10 movie/state pairs were the
relevant natural damage leads, so no operator recording was duplicated or
requested. Every state was inspected before load as format 84, `SCUS-94288`,
with embedded and mounted media hashing to the pristine retail pins.

`tools/phase4_lives_death_breadth.py` replays each complete movie twice through
`movie.traceToFrame`: an uninstrumented cached-interpreter control and passive
coverage over resident damage, scene-flow and respawn ranges. All eight pairs
finish with equal RAM, registers, cycle and frame and no trace truncation.

Observation:

- scene 6 and the scene 3/10/4 pit leads complete ordinary respawn, each with
  exact `0x800500F4`, `0x8005B30C`, and `0x8005B348` coverage, health 4, and a
  one-life decrement;
- the scene-12 lead reaches health/lives `1/0 -> -1/0`. Its 660-frame source
  ends before selection, so the first strict guard correctly rejected a
  game-over claim. A transient 240-frame neutral suffix then executes the exact
  final-life reader and selector `0x800500BC/0x800500D4`, with zero respawn-tail
  hits; and
- the other three source-complete paths are nonfatal boundaries at health
  `4->3`, `1->0`, and `4->2` with no respawn-tail execution.

Inference: five natural deaths across scene values 3, 4, 6, 10 and 12 traverse
the same resident C16 final-life/ordinary-respawn law. The trace establishes
executed control flow, not why each source caused damage.

Causal boundary: no trigger-causality or E10 ownership is claimed. Filenames do
not identify hazard kinds, scripted/special status, actors, trigger writers, or
persistence. That frontier remains open even though the shared resident law is
now directly reproduced.

The initial guarded attempt used fresh config
`/tmp/abl-phase4-i13-c16-breadth-20041`, stopped only owned PID 1656804, and
retained no artifact because the source-only scene-12 horizon did not contain
the selector. The final run used
`/tmp/abl-phase4-i13-c16-breadth2-20042`, port 20042, and stopped only owned PID
1656997. The retained artifact is
`analysis/phase4_lives_death_breadth.json`, SHA-256
`21307ab806e3c56331a29d6bdfa733eea943c843be3ffdf71096dd66621ccd0c`.

## Iteration-14 first transition-producer attribution

The same eight pinned pairs were replayed after a fresh recursive movie census;
no new operator fixture was consumed. A pristine static scan first enumerated
all exact `jal 0x8004A700` words: six in `SCUS_942.88` and two in verified
Region-A overlay inputs. Every live replay then used cumulative passive
coverage to binary-search the first target entry. At the preceding movie frame,
an isolated diagnostic replay ran to a breakpoint at `0x8004A700`, waited for
the stable paused boundary, and retained `$ra`, the link word, arguments and a
runtime code-slice hash. A separate cumulative search found the first health
store or respawn-lives store and verified the adjacent typed outcome.

Observation:

- acorn-named input enters from proximity call `0x8004B4A0`;
- falling-rocks and falling-spikes inputs enter from contact-walker call
  `0x80058A48`;
- goo-named input enters from player region-code-4 call `0x80049740`;
- all three pit inputs enter from player region-code-1 call `0x800496B0`; and
- the ground-bird-named input enters from `0x800B3E94` with `a3=3`. Its runtime
  36-byte slice matches pristine `LEVEL06/LEVEL.BIN` even though the current
  scene value is 6 and the static scene annotation does not match. Its typed
  lives decrement follows 119 movie frames later.

Inference: the eight paths now have exact first native producer-call
boundaries, and the five death paths remain joined to the resident C16 law.
The last mapping directly demonstrates why neither a filename nor a scene
serial is media/ownership proof.

Causal confirmation: each passive target/caller/effect coverage pass remains
RAM/register/cycle/frame equal to its uninstrumented cached-interpreter replay.
The entry breakpoint is a separate pinned replay used only for architectural
link/argument capture. Its caller is accepted only when `$ra-8` decodes as a
link instruction resolving to `0x8004A700` and the static/runtime code identity
matches.

Rejected methods and hypotheses:

- Health/lives inequality is not a monotonic trigger-search predicate: the
  ground-bird lead restores health before its later lives decrement.
- `0x8004A888` is not universal for transition outcomes: region-code-1 and the
  overlay path reach the respawn lives store instead.
- The immediate status returned by `debugger.runUntilAddress` is the resumed
  status, not necessarily the later breakpoint stop. Reading registers without
  polling produced a mid-dispatch `$ra`; reverse stepping exposed the race and
  independently recovered acorn caller `0x8004B4A0`.
- The ground-bird filename does not prove a bird trigger. Runtime bytes and
  arguments identify an overlay transition producer instead.

The final isolated source-refresh run used config
`/tmp/abl-phase4-i39-c16-breadth-sourcefinal-5kWg50`, port 20682, and stopped
only owned PID 95367. The current artifact SHA-256 is
`af9fb1c5d3900b2eea00714d491f785f33d45151a1e5c7ecd553001069e0c01e`;
generator SHA-256 is
`2982ba1da1d3c08490e8672cd7334c95fc0b5e621b80b1f9fabb192f744df669`.

## Iteration-15 frontend/card correction

The prior experiments established the exact fourth-Start input split and lives
writer but did not inspect the displayed frontend state. The new run reused the
same centrally pinned movie/save pair after a fresh recursive movie census. It
started DuckStation through the repository launcher with an isolated card
copied from the centrally declared, hash-pinned seed. Load-free save inspection
and live media identity again proved pristine `SCUS-94288` before replay.

Observation: the transient frame at movie frame 3662 is the title screen, not a
Continue selection. Natural Start frames 3663–3669 reach scene 0/lives 5 and a
stage-select frame by 4006. Removing only those seven samples leaves scene
0/lives 0 on the title screen. The three exact transient pixel hashes are
retained in `analysis/phase4_c16_frontend_card.json`; the images themselves
were deleted.

The E14 interface join bounds the bidirectional native card copy to the
336-byte resident progress block `0x8009EC68..0x8009EDB7`. Lives
`0x800A65A0` is outside that range. At movie frames 0, 3662, 3700, and 4006,
the natural and Start-removed branches retain the same progress-block SHA-256
`611fc682fd1235862b4656dd2a2920beb89ee79b1032ae18ce91a0b34a5c0418`.
The isolated card remains equal to seed SHA-256
`63c08f0143e7b714309de900905f22944ae07f1da881ce9aa3a0237a5dacf517`;
its final diff contains zero changed bytes.

Correction: the fourth Start is a post-game-over title restart whose scene
initialization writes lives 0 to 5 at `0x80055550`. It is not evidence of a
separately presented Continue menu choice. This narrow path performs no card
write; explicit native Save/Load, no-card/corrupt-card behavior and other menu
paths remain open. The old artifact's schema-stable `continue_transition`
member and historical fixture/note filenames are not current semantic claims.

The successful isolated run used config
`/tmp/abl-phase4-i15-c16-frontend-20064`, port 20064, and stopped only owned PID
2031682. The retained artifact SHA-256 is
`07116d292129ea581a8a96ca3122b84ba600ca4444ce4fc336a680dc5b0eb7e6`;
generator SHA-256 is
`23e9014fd5b2ae660676b5d76b819f14e7611c9066af3465edcebda42ac24ef5`.

## Iteration-16 Stage-15 boss-context fatal caller

The mandatory recursive census again found 110 Phase-4 files and 147 files in
the broader movie tree. The already declared `hopper_boss.movie.json` and
`hopper_boss.movie.sav` pair was the relevant boss/bonus/scripted lead; no
operator recording was duplicated, imported, or requested. The movie hashes to
`43fc92b9085007480860946d5cf66d5272c239f4e54e51b48ab3b1e1b5c40ed7`,
the save hashes to
`003209bfe7566234b337620236b6bf00f8ec560dfd1c48a26886ecb565fb97b7`,
and load-free state inspection plus mounted-media hashing prove pristine
`SCUS-94288` before replay.

Observation: the v1 recording begins in scene 15 at health/lives `2/0` and
first reaches fatal health at movie frame 1047. The retained passive traces at
the bracketing frames and complete source horizon are RAM/register/cycle/frame
equal to their uninstrumented cached-interpreter controls. Scene remains 15;
the exact resident fatal-health, final-life-reader and game-over-selector PCs
all execute.

Inference: scene 15 maps through the authoritative scene graph to
`level05\level5c`, and the existing D20/F15 fixture routes make this a Canyon
Showdown boss context. Save-restored Region-A hashes match neither staged
LEVEL05 candidate, so no exact live overlay file identity is inferred.

Causal confirmation: a separate fresh replay stops at the next
`0x8004A700` entry after the nonfatal boundary. `$ra=0x8004B4A8` resolves to
the resident proximity-updater `jal` at `0x8004B4A0`; running that one
invocation to its architectural return changes health `0 -> -1` and master
state `0 -> 2` while lives stays 0 and scene stays 15. This proves the exact
proximity-contact producer and resident game-over law. It does not prove that
Hopper or another actor supplied the contact and does not complete D20/F15.

Two guarded dry runs corrected a v1-specific timing assumption before any
artifact was retained. For v1 playback, target `N` consumes through zero-based
input index `N-1`, and this fork reports `playing=true` with the last index at
EOF. The shared v3 helper was not weakened; the v1 convention is local to this
generator. Both failed isolated configs were cleaned through their owned
pidfiles. The final run used
`/tmp/abl-phase4-i16-c16-boss-final4-20079`, port 20079, and stopped only owned
PID 2337234. The retained artifact `analysis/phase4_c16_boss_death.json` now has
SHA-256 `c6faf754642f716dad42df3aa42034cd015fd633567ac26b4049806d00a348f9`;
generator SHA-256 is
`c51e2eafaf6dbef1be948bf134cb77bdc8b17f3d591c3eed14e86b53367ac0a7`.
Those lines identify the original semantic run. Iteration 19 replayed the
unchanged result after the authoritative mechanics hash changed, using fresh
config `/tmp/abl-phase4-i19-refresh-boss-20178`, port 20178, and owned PID
3289593; that source-fresh replay supplies the current artifact provenance.

## Iteration-17 Bonus-3 one-field contact-death control

The mandatory recursive census again found 110 files under the Phase-4 movie
tree and 147 files in the broader tree. The already declared
`movies/Bonus_Level_03.movie.json` and `.sav` pair was the relevant bonus lead,
so no operator recording was duplicated, imported or requested. The movie
hashes to `22ef450e2a88edcd7b3ef52bdfde7dc7cceff37d2967d37f377403bc6d7bf984`
and the save to
`0dd145be44878df0424eee7942c9f645d4b0961e1bfe0a831e6acf0538d6b522`.
Load-free state inspection and mounted-media hashing prove pristine
`SCUS-94288` before replay.

Observation: natural v3 input in scene 3 changes true health `1 -> 0` between
movie frames 210 and 211 while lives remains 5 and master state remains 0.
Phase-2 stage routing and the state values establish Bonus-3 context only.

Causal confirmation: at the exact frame-210 control boundary, a `writeU16`
changing true health 1 to 0 changes only RAM byte `0x800A6594`. The same native
input then produces health -1/master state 2 at frame 211 and ordinary respawn
health/lives `4/4`, master state 0, at frame 331. A separate fresh replay stops
at transition entry `0x8004A700`; `$ra=0x8004B4A8` and the link word prove
proximity call `0x8004B4A0`, and the single invocation returns with the fatal
state. Internally control-checked cached-interpreter traces retain every
required proximity, damage, scene-flow and respawn PC without changing RAM,
registers, cycle or frame relative to their own uninstrumented controls.

Bounded method result: the transient derivative save/movie suffix is deleted
after use. Two fresh isolated iteration-34 refresh attempts supersede the
earlier one-cycle/full-RAM difference: typed state, emulator frame, PC/SP,
registers, cycle and full RAM now all equal the direct terminal. The retained
guard requires this exact relation. An earlier `debugger.hashMemory` hypothesis failed with method-not-
found because the current 203-method fork has no such RPC; the generator instead
hashes main RAM through two bounded one-MiB reads. Two attempts to collect
coverage after an in-place mid-movie write produced zero hits under the
configured recompiler transition and were rejected; the internally neutral
suffix trace is the retained evidence.

Inference is deliberately narrow: this is a proximity-contact ordinary death
in a Bonus-3 context. The filename does not prove a grasshopper, attack, actor,
reward or F18 behavior. No MOD-private state, hook, cave or intended behavior
was added, so no Mods note applies.

The final source-dependent run used fresh config
`/tmp/abl-phase4-i17-c16-bonus-final7-20125`, port 20125, and stopped only owned
PID 2634169. Retained artifact
`analysis/phase4_c16_bonus_death.json` now has SHA-256
`310b4c824eb6af1261034bbe024ce88a9a29f92b43164be55a2db9c95478d553`;
generator SHA-256 is
`40482f5039fcb70c7bde36d4a7569b4902b48142731fb72e2f80ed8db8d44ba6`.
Those lines identify the original semantic run. Iteration 19 replayed the
unchanged result after the authoritative mechanics/row-coverage hashes changed,
using fresh config `/tmp/abl-phase4-i19-refresh-bonus-20177`, port 20177, and
owned PID 3289453; that source-fresh replay supplies current provenance.

## Iteration-18 Thumper actor-owned death control

The mandatory recursive census found 110 files under the Phase-4 movie tree
and 147 files in the broader tree before campaign selection. The complete,
already declared `thumper_boss_2.movie.json` and `.sav` pair was the relevant
boss/scripted lead; the Bird cinematic was explicitly rejected after replay
showed lives did not select its scene transition, and no operator recording was
duplicated or requested. The Thumper movie SHA-256 is
`c5e26e960e10627963d3f419e38868384439c5477d525f1972c0c87288d2bad5`;
the save SHA-256 is
`991d50d2af1513e3fd746711b8e70936d7674aab44ece21d3262e6bac0efe282`.
Load-free format-84 state inspection and mounted-media hashing proved pristine
`SCUS-94288` before replay.

Observation: natural v2 input in scene 2 changes health `4 -> 3` between movie
frames 2422 and 2423 while lives remains 4 and master state remains 0. Passive
cached-interpreter traces at both boundaries match their uninstrumented RAM,
registers, cycle and frame and retain proximity call `0x8004B4A0` plus fatal-
health store PC `0x8004A888` as the executed damage routine.

Inference: the authoritative scene graph maps scene 2 to
`level03\level1b`/`stage03_council_chamber`, and the existing Phase-2 route
establishes D16 Thumper boss context. The context and filename alone are not
actor ownership evidence.

Causal confirmation: two fresh replays stop at the next `0x8004A700` entry and
run exactly to architectural return. Natural and one-field-fatal controls have
the same `$ra=0x8004B4A8`, link word, arguments and `$s1=0x8009FE04`. That live
record is fixed pool slot 1/id 16/callback `0x8004A0F4`/backlink `0x80094A54`;
the neighboring slot 2 is independently id 10/callback `0x8004A180`. Changing
only true health `4 -> 0` changes exactly byte `0x800A6594`; the same invocation
then returns at health -1/master state 2 and reaches ordinary respawn
health/lives `4/3`, scene 2, master state 0 at frame 2550. This confirms one
Thumper-owned proximity attack, not the complete D16/F03 encounter.

The declarative scenario independently passed all 16 typed/reproducibility
assertions. Its transient report at
`/tmp/abl-phase4-i18-thumper-scenario/pristine_thumper_actor_death.json` hashed
to `ab8cbd619b7374c2c0c8b445f4a3184b1800647f2ef4d4b0aacd8831fb503bc2`;
the report remains outside Git. The final source-dependent generator run used
fresh config `/tmp/abl-phase4-i18-thumper-final-20151`, port 20151, and stopped
only owned PID 3060802. The retained artifact
`analysis/phase4_c16_thumper_death.json` has SHA-256
`0024a7c7012909b05f7fa04dba55b49518881bf4a057aeb59b5984b2e51928dd`;
generator SHA-256 is
`c488dd7cc73ef6bdb5d7fdf9f8b85993853706a08eb4dcdf1262789d42338ccb`.
Iteration 19 replayed the unchanged result after the same authoritative source
change, using fresh config `/tmp/abl-phase4-i19-refresh-thumper-20179`, port
20179, and owned PID 3289742; that source-fresh replay supplies current
provenance.
The shared mechanics update correctly invalidated and forced fresh Bonus-3 and
Stage-15 artifacts; their current hashes are respectively
`654a71819a7d27704a4b01decfc0f5630fd00a652ae9f07099abe029fc7d12fa` and
`4794d534a6b3118e9d584faa2a98be7785fa596cf9ed1e29719551e6f6d22f4b`.
Iteration 20 replayed all three unchanged C16 results after the D18/F09
mechanics update: Bonus-3 used config
`/tmp/abl-phase4-i20-refresh2-bonus-20207`/PID 3611600, Stage-15 used
`/tmp/abl-phase4-i20-refresh2-boss-20208`/PID 3611733, and Thumper used
`/tmp/abl-phase4-i20-refresh2-thumper-20209`/PID 3611884. Each generator stopped
only its owned PID; the current Thumper artifact hash is
`400450859b8e1ed68e0c5e4a43471c2629b9cf208b2d96110b68a54ca24dcb30`.

Iteration 23's date-bound source refresh replayed all four Event-VM consumers
on separate fresh isolated pristine-media instances. After the first E07
candidate was rejected for the known 42-fetch timing desync, the final Bonus-3
refresh used `/tmp/abl-phase4-i23-c16_bonus2-refresh-20340.GJUnGo`/PID 278872,
Stage-15 used `/tmp/abl-phase4-i23-c16_boss2-refresh-20341.38VxrG`/PID 278876,
Thumper (which does not consume E07) used
`/tmp/abl-phase4-i23-c16_thumper-refresh-20336.FLrLoH`/PID 274721, and the
eight-anchor breadth join used
`/tmp/abl-phase4-i23-c16-breadth3-refresh-20346.gtRi1A`/PID 282898. Each
generator reverified mounted/save media and stopped only its owned PID. The
source-fresh hashes are Bonus-3
`310b4c824eb6af1261034bbe024ce88a9a29f92b43164be55a2db9c95478d553`,
Stage-15 `c6faf754642f716dad42df3aa42034cd015fd633567ac26b4049806d00a348f9`,
Thumper `0024a7c7012909b05f7fa04dba55b49518881bf4a057aeb59b5984b2e51928dd`,
and breadth `af9fb1c5d3900b2eea00714d491f785f33d45151a1e5c7ecd553001069e0c01e`.
The behavioral outcomes are unchanged; the replay exists to discharge exact
source-dependency freshness, not to promote any C16/D16/F03 frontier.

Iteration 26 changed the shared mechanics source while banking Thud's action-20
billboard, so the three affected C16 artifacts were invalidated and replayed
rather than accepted from stale summaries. Bonus-3 used fresh config
`/tmp/abl-phase4-i26-c16-bonus-final-20458.BlbvyI`, port 20458, PID 981866;
Stage-15 used `/tmp/abl-phase4-i26-c16-boss-final-20459.0RY91U`, port 20459,
PID 982001; Thumper used
`/tmp/abl-phase4-i26-c16-thumper-final-20460.KijTHu`, port 20460, PID 982150.
Each run reverified pristine mounted/save media, reproduced the unchanged low-
level behavior and stopped only its owned PID. The current artifact hashes are
Bonus-3 `e188099d32223bcf5106a7d89aaa4780ac79b0179fe214ad400d3cf55ece2545`,
Stage-15 `be759e04cc2b8248b583a7b52c08094b1f90bf904f71f5ff677062cbd3d075a7`
and Thumper `a7995eba043aaf146b3790ea9af28dc509da6e27b65441c587cf6b2e5589a34d`.
This source-freshness replay does not extend any C16/D16/F03 conclusion.
No MOD-private state, hook, cave or intended behavior was introduced.

Iteration 27 changed the shared mechanics source again while binding the Thud
action-20 sound call. Fresh isolated pristine replays on ports 20473, 20474 and
20475 reproduced the same Bonus-3, Stage-15 and Thumper outcomes, verified each
declared mounted/save-media identity and stopped only the owned instance. Their
new source-fresh hashes are respectively
`ddac4d0c16531d4c4d1f94ade57c76fe54a97816a31e69efefc0b9ce7886de02`,
`a1c88e0fe4a4c541efbc8717989f8e6cede88259dc27a011de1524c1a9481989`
and `e9f4401ee8192d23c1eeebb8a6ff6bfd457733ee383bcd314e409451bcc48c76`.
The replay is dependency maintenance and promotes no C16/D16/F03 frontier.

## Reproduction

After provisioning centrally declared external inputs, launch a pristine disc
in a fresh isolated debugger config and run:

`python3 tools/phase4_lives_gameover.py --port <port> --token <token> --config-dir </tmp/config> --instance-state recreated`

The supporting multi-scene law join is regenerated separately so its eight
dependency fixtures cannot silently confer campaign completion:

`python3 tools/phase4_lives_death_breadth.py --port <port> --token <token> --config-dir </tmp/config> --instance-state recreated`

The Stage-15 boss-context join is regenerated independently:

`python3 tools/phase4_c16_boss_death.py --port <port> --token <token> --config-dir </tmp/config> --instance-state recreated`

The Bonus-3 context control is regenerated independently:

`python3 tools/phase4_c16_bonus_death.py --port <port> --token <token> --config-dir </tmp/config> --instance-state recreated`

The actor-owned Thumper control is regenerated independently:

`python3 tools/phase4_c16_thumper_death.py --port <port> --token <token> --config-dir </tmp/config> --instance-state recreated`

The stable natural path is also the declarative scenario
`tools/scenarios/duckstation/pristine_lives_gameover_continue.yaml` (SHA-256
`0183e824bee0a2e36eec1981ea10695da0c21102b30735a40b0f2968341c0604`):

`python3 tools/run_ps1_scenario.py tools/scenarios/duckstation/pristine_lives_gameover_continue.yaml --output-dir /tmp/abl-phase4-i9-c16-scenario-report`

Its assertions retain the final-life and title-restart boundaries; the
historical filename is stable but no longer labels the fourth Start as a
Continue choice. Low-level falsification guards are in
`tests/test_phase4_lives_gameover.py` and
`tests/test_phase4_c16_frontend_card.py`. The boss-context regression is
declarative in
`tools/scenarios/duckstation/pristine_hopper_context_final_life.yaml`, with
low-level guards in `tests/test_phase4_c16_boss_death.py`.
The bounded Bonus-3 control is declarative in
`tools/scenarios/duckstation/pristine_bonus3_contact_death.yaml` (SHA-256
`5aa8b1e83da28e5f46b6467f9712614c694fc00c94b77487eeb4ae0bbc03196f`),
with low-level guards in `tests/test_phase4_c16_bonus_death.py`.
The Thumper control is declarative in
`tools/scenarios/duckstation/pristine_thumper_actor_death.yaml` (SHA-256
`5770cd45fb8cbd53c258a95156df6abbb27689790f4ab4b2770df4a59a04a316`),
with low-level guards in `tests/test_phase4_c16_thumper_death.py`.

## Iteration 33 — Thud row-4 final-life control

The required recursive inventory found 110 Phase-4 and 147 broader movie-tree
files. This experiment reused the already central, complete
`thud_boss_movie.movie.json/.sav` pair; it requested and imported no new
operator recording. Load-free state inspection and live media queries verified
the pinned pristine CUE/BIN before replay.

The first exact-call run falsified the hypothesis that `$s2` still names the
winning arena row at resident entry. At `0x8004A700`, `$s2=6`: the overlay has
already completed its six-row loop. That failed run retained no evidence and
stopped only PID 2356987. The corrected causal predicate reads all six live rows
at the exact entry and requires row 4 to be the sole in-threshold row; this is
also independently joined to the cycle-neutral row-4 arena artifact.

Fresh natural and controlled runs share target 1465 with identical cycle,
frame, PC/SP, RAM and register identities before mutation. The controlled run
changes only byte `0x800A6594`, true health `3 -> 0`. Both stop at
`jal 0x800B4AE0 -> 0x8004A700` and return to `0x800B4AE8` with the same
arguments. The natural result is health/master `2/0`; the controlled result is
`-1/2`, with lives 0 in both. At entry, row 4 alone has distance 454805 below
threshold 490000, speed 110 and ramp 0.

The retained artifact SHA-256 is
`027e92f7c6db9c81460d8e44643ada39c805db3aefdf39b951b78a064682e719`.
Its fresh isolated run stopped only PID 2424798. The earlier declarative probe
and final scenario both use only the same health-field edit; the retained
scenario SHA-256 is
`1a3bb9e4c3940a0fec54bcd176da3a82ed37eec6128dcf2636cb74e0644b869c`.
No movie, save, disc, capture, token, or derivative state is committed.

This result is one boss-arena contact joined to C16 final-life selection. It
does not establish a scripted, special, or exceptional class and does not
complete C16, D18, or F09.

Regenerate the live artifact in a fresh isolated pristine instance with:

`python3 tools/phase4_c16_thud_boulder_death.py --port <port> --token <token> --config-dir </tmp/config> --instance-state recreated`

Run the declarative regression with:

`python3 tools/run_ps1_scenario.py tools/scenarios/duckstation/pristine_thud_boulder_final_life.yaml --output-dir /tmp/abl-phase4-c16-thud-boulder`

Low-level mutation and open-gate guards are in
`tests/test_phase4_c16_thud_boulder_death.py`.

## Iteration 34 — Riverbed Flight actor-contact control

The mandatory recursive census reproduced 110 files under `movies/Phase4`
and 147 under the broader movie tree. No dedicated scripted/setpiece death
recording was substituted. The experiment reused centrally pinned pristine
`level_14.sav` (SHA-256
`6e56d8c4780851f85059b477186b5b1346e23ed7e8eac79a134192e03fef5f50`)
and generated its neutral trace movies/states only in `/tmp`.

Observation: after a bounded synthetic proximity setup, scene 8 reaches a
matched frame-223793 origin with health/lives `0/3`. Corrected live pool slot 5
at `0x800A0014` is id 37, callback `0x80049E88`, source `0x80094AC4`, type word
`0x0125`. At frame 223794, the next damage entry has
`$ra=0x8004B4A8`, `$s1=0x800A0014` and `$a3=0`, binding exact call
`0x8004B4A0 -> 0x8004A700`. It returns with health -1/master 2; by frame
223973 the native ordinary respawn is health/lives `4/2`, scene 8.

Inference: scene routing establishes a Riverbed Flight context. The retained
E08 type-word frontier still classifies `0x0125` as unclassified, so neither a
species name nor a special/scripted class follows from the context.

Causal confirmation: at matched frame 223793, setting only actor state bit
`0x0080` changes exactly main-RAM byte `0x800A0070` from `0x11` to `0x91`.
At the equal frame/cycle/PC/SP endpoint, health/lives remain `0/3`, with zero
damage-range hits, no proximity call `0x8004B4A0`, and zero respawn-range hits.
Natural 180-frame coverage contains 112 damage-range hits and 978 respawn-range
hits, including `0x8004A888`, `0x800500F4`, `0x8005B30C` and `0x8005B348`.

Rejected hypothesis: setting the same bit at the save/setup anchor is not a
valid control. The native actor update overwrites it back to `0x4011` before
contact and the branch still dies. This failure is retained separately from
the successful matched-boundary intervention.

The final source-fresh generator run used isolated config
`/tmp/abl-phase4-i34-flight-final3.Qd07lK`, port 20563, and stopped only PID
2653394. Artifact SHA-256 is
`bfa593ae8c2620fadbe52e46ce01ac5949087fa1e35744611e74afd457ad4114`;
scenario SHA-256 is
`7d2245ef9fabe4b262e2010db97fd6f68d971b49a4ec565d889891cd1594d1e6`.
The corrected declarative run passed 15/15 assertions, stopped only PID
2660563, and left transient report SHA-256
`a161d533d641e8c247cb848228c6279855c1cc40646278ceb48f077cce4dd29a`.
No movie, save, state, disc, capture, BIOS, token or generated media is committed.

Regenerate with:

`python3 tools/phase4_c16_flight_death.py --port <port> --token <token> --config-dir </tmp/config> --instance-state recreated`

Run the declarative response-only regression with:

`python3 tools/run_ps1_scenario.py tools/scenarios/duckstation/pristine_riverbed_flight_actor37_death.yaml --output-dir /tmp/abl-phase4-c16-flight`

## Ratchet continuation iteration 1 — Bonus-3 terminal accounting

Two new isolated Bonus-3 refresh attempts, one with the default recompiler
profile and one with the movie-replay cached-interpreter profile, reproduced
the same terminal relation. The transient suffix ends exactly one CPU cycle
earlier than the direct branch and has a distinct full-RAM digest, while
registers, PC/SP, emulator frame and typed scene/master/health/lives state are
equal. Both attempts rejected the iteration-34 bit-identical expectation and
stopped their owned instances before any artifact write.

The generator now retains this exact bounded relation and both terminal RAM
hashes. This supersedes only the iteration-34 full-machine-equality claim; the
one-byte health intervention, exact proximity invocation, cycle-neutral PC
coverage and ordinary-respawn outcome remain independently guarded.
