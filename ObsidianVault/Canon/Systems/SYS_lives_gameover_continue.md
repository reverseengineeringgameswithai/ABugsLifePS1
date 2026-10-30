---
kind: system
id: SYS_lives_gameover_continue
created: 2026-07-16
updated: 2026-07-17
status: live_confirmed
confidence: high
source_state: original_game
functions: [0x8004A700, 0x8004FCA0, 0x80055538, 0x8005B12C, 0x8005B714]
memory: [0x800A6594, 0x800A65A0, 0x800823A0, 0x80082470, 0x80082504]
evidence: [EXP_2026-07-16_phase4_lives_gameover_continue, analysis/phase4_lives_gameover.json, analysis/phase4_lives_death_breadth.json, analysis/phase4_checkpoint_respawn.json, analysis/phase4_c16_frontend_card.json, analysis/phase4_c16_boss_death.json, analysis/phase4_c16_bonus_death.json, analysis/phase4_c16_thumper_death.json, analysis/phase4_c16_thud_boulder_death.json]
src_paths: [tools/phase4_lives_gameover.py, tools/phase4_lives_death_breadth.py, tools/phase4_c16_frontend_card.py, tools/phase4_c16_boss_death.py, tools/phase4_c16_bonus_death.py, tools/phase4_c16_thumper_death.py, tools/phase4_c16_thud_boulder_death.py, config/phase4_lives_gameover.yaml]
patch_policy: safe_to_read
---

# Lives, game over, ordinary respawn, and title restart

## Confirmed resident law

The player stores true health as signed `s16` at `0x800A6594` and lives as
`u8` at `0x800A65A0`. Damage at `0x8004A888` writes the decremented health;
death begins only below zero. Lives zero is therefore a playable final life,
not an already exhausted count.

When scene-flow state 2 runs, `0x800500BC` reads lives:

- lives zero follows the game-over branch through the movie selector at
  `0x800500D4` and reaches scene 0;
- lives nonzero calls the alternate entry `0x8005B12C`, whose common respawn
  tail restores health to 4 at `0x8005B30C` and stores lives minus one at
  `0x8005B348`.

The dedicated pristine Bug Bar recording reproduced both decisions from one
anchor. Natural movement with health 1/lives 0 reached health -1 and game over.
Changing only the starting lives byte from 0 to 1 selected same-scene respawn,
health 4, lives 0. Neutralizing only movement frames 40 through 121 caused no
damage and no damage-region execution.

## Post-game-over title restart

The recording contains four Start bursts. Both compared branches are identical
through movie frame 3662, whose transient captured frame is the title screen.
The natural fourth burst (frames 3663 through 3669) executes
`scene_config_apply`; its exact `sb` at `0x80055550` writes lives 0 to 5 and
the replay reaches the stage-select screen by frame 4006. Removing only those
seven Start samples leaves the replay on the title screen with lives 0 through
frame 4006. This is a post-game-over title restart, not evidence that the game
presented or selected a Continue menu choice. The historical fixture and note
names are retained only as stable identifiers.

The E14-owned native card serializer copies exactly 336 bytes at
`0x8009EC68..0x8009EDB7` in both directions. Lives `0x800A65A0` is outside
that block. In a freshly seeded isolated card, the natural and Start-removed
branches retain the same progress-block SHA-256
`611fc682fd1235862b4656dd2a2920beb89ee79b1032ae18ce91a0b34a5c0418` and
the card remains byte-identical to its seed at every sampled boundary; the
final card diff has zero changed bytes. This proves that this particular title
restart resets nonserialized lives without a host-card write. It does not
describe explicit native Save/Load or any other frontend path.

## LEVEL02 pit join

A separately pinned LEVEL02 pit path starts at health/lives `3/5` and naturally
reaches `4/4` by movie frame 160. Replacing only input frames 57–87 with the
source-neutral pad leaves `3/5` and never executes the respawn handler. This
adds one pit death/reset class and a second stage. The stable position is not
controlled by a frame-100 safe-X mutation, even with the continuous safe-anchor
stores suppressed. C15 now identifies its later owner as overlay `0x800B3C54`
selecting a scene-local row before resident `0x8005B134` consumption; broader
death-class and overlay policy remain C15 boundaries.

## Bug Bar safe-anchor join

The same one-byte lives-1 ordinary contact path now has a C15-owned positional
control. At fatal movie frame 350, changing only retained safe X by `+4096`
changes first-completed-respawn live and safe X by exactly `+4096` at frame
355. Y/Z, scene and this campaign's health/lives result `4/0` are unchanged,
and the two branches have identical updater, resident-handler and overlay-window
coverage. This binds safe-anchor consumption into the already confirmed
ordinary-respawn lifecycle without transferring broader checkpoint or hazard
ownership to C16.

## Multi-scene resident-law join

Eight existing centrally pinned natural damage recordings were replayed from
their inspected pristine states with complete cycle-neutral resident coverage.
Four naturally complete ordinary respawns in scene values 3, 4, 6 and 10 all
execute `0x800500F4`, restore health at `0x8005B30C`, and decrement lives at
`0x8005B348`. A fifth natural death starts and ends its recorded input in scene
12 at health/lives `1/0 -> -1/0`; its source movie ends before scene-flow
selection, so a transient 240-frame neutral suffix proves the same final-life
reader and game-over selector `0x800500BC/0x800500D4` without changing the
operator recording. Three other complete leads remain bounded nonfatal damage
at health `4->3`, `1->0`, and `4->2`; they do not enter respawn.

Every passive coverage pass exactly matches its own uninstrumented RAM,
registers, cycle and frame. This confirms shared resident execution across five
natural death paths.

The first entry into `0x8004A700` is now caller-bound for all eight recordings.
Fresh-anchor cumulative coverage locates the first entry; an isolated
entry-breakpoint capture then proves `$ra = caller + 8`, the link instruction,
arguments, and resolved target. The exact producer paths are:

- proximity updater `0x8004B4A0` for the acorn-named lead;
- contact-pool walker `0x80058A48` for both falling-object-named leads;
- player region-code-4 branch `0x80049740` for the goo-named lead;
- player region-code-1 branch `0x800496B0` for all three pit-named leads; and
- overlay call `0x800B3E94` for the ground-bird-named lead.

That last result is the important corrective. Its runtime 36-byte call slice
exactly matches pristine `LEVEL06/LEVEL.BIN`, and entry argument `a3=3`; the
declared scene metadata does not match the live scene value 6. The transition
precedes the first typed `4/4 -> 4/3` result by 119 movie frames. This is an
exact native producer-call fact, not evidence that a bird caused damage.

These caller joins do not identify hazard kind, script/actor owner, or
persistence policy. The filenames remain discovery metadata and E10 retains
those questions.

## Stage-15 boss-context final-life join

The centrally declared `hopper_boss` movie/state pair starts in verified live
scene 15 with health/lives `2/0`. The authoritative scene graph maps scene 15
to `level05\level5c`, and the existing D20/F15 fixture routes identify this as
the Canyon Showdown boss context. Natural v1 input reaches the first fatal
boundary at movie frame 1047.

A fresh replay stopped at the next `0x8004A700` entry and ran exactly one native
invocation to its architectural return. Entry `$ra=0x8004B4A8` resolves to the
resident proximity-updater `jal` at `0x8004B4A0` (word `0x0C0129C0`). In the
same emulator frame, health changes `0 -> -1`, master state changes `0 -> 2`,
and lives and scene remain `0` and `15`. Passive coverage also contains fatal
health store `0x8004A888`, final-life reader `0x800500BC`, and game-over movie
selector `0x800500D4`, with RAM/register/cycle/frame equality to the
uninstrumented replay.

This confirms a proximity-contact death in a Stage-15 boss context. It does
not prove Hopper or another actor caused the contact. The save-restored
Region-A bytes match neither staged `LEVEL05_LEVEL.BIN` nor
`LEVEL05_LEVEL1.BIN`, so the runtime overlay is not promoted to either exact
file identity. D20 Hopper behavior, F15 objective completion, actor ownership,
and other boss death paths remain open.

## Bonus-3 context ordinary-death join

The centrally declared `Bonus_Level_03` v3 movie/state pair starts in verified
scene 3 at health/lives `1/5`. Phase-2 routing and the pinned state establish a
Bonus-3 context. Natural input changes health `1 -> 0` between movie frames
210 and 211 without selecting death.

At the identical frame-210 cycle/RAM/register boundary, changing only true
health `0x800A6594` from 1 to 0 changes exactly one main-RAM byte. The next
native contact stops at `0x8004A700` with `$ra=0x8004B4A8`, proving the
resident proximity-updater `jal` at `0x8004B4A0` (word `0x0C0129C0`). Running
that invocation to return changes health `0 -> -1` and master state `0 -> 2`
while scene/lives remain `3/5`. By movie frame 331, the resident ordinary-
respawn law has restored health to 4, decremented lives to 4, and cleared
master state. Passive traces contain the exact fatal-health, scene-flow,
ordinary-respawn, health-restore and life-decrement PCs and match their own
uninstrumented RAM/register/cycle/frame controls.

The transient save/reload suffix is an independent inspection anchor. Two fresh
isolated iteration-34 refresh replays supersede the earlier one-cycle/full-RAM
difference: suffix and direct terminals now match in full RAM, registers, cycle,
PC/SP, emulator frame and typed lifecycle outcome. The generator requires that
exact relation before retaining the internally control-checked coverage result.

This confirms one proximity-contact ordinary death in a Bonus-3 context. The
filename and Phase-2 F18 route do not identify a grasshopper, actor, attack,
reward or permanent-kill rule, so F18 and other bonus-death contexts remain
open.

## Thumper actor-owned ordinary-death join

The centrally declared complete `thumper_boss_2` v2 movie/state pair starts
from inspected pristine media and reaches a natural hit in live scene 2.
Between movie frames 2422 and 2423, health changes `4 -> 3` while lives stays 4
and master state stays 0. Scene 2 maps to `level03\level1b` and the Phase-2
`stage03_council_chamber` route.

Fresh natural and one-field-fatal replays stop at the exact next damage entry.
Both have `$ra=0x8004B4A8`, proving proximity-updater
`jal 0x8004B4A0 -> 0x8004A700` (word `0x0C0129C0`), with the same arguments.
Crucially, both carry `$s1=0x8009FE04`. The live actor record at that address is
fixed-pool slot 1, id 16, callback `0x8004A0F4`, VM IP `0x8007764E`, HP 24 and
authored-record backlink `0x80094A54`. The adjacent record at `0x8009FE88` is
separately slot 2/id 10/callback `0x8004A180`. This corrects the older
documentation-only `slot0/slot1` labels: the fixed pool starts at
`0x8009FD80`, so these addresses are slots 1 and 2.

At the exact frame-2422 boundary, changing only true health `4 -> 0` changes
one main-RAM byte, `0x800A6594`. The same actor-bound invocation then returns
at health -1/master state 2 while lives remains 4. By frame 2550, the ordinary
resident lifecycle has restored health to 4, decremented lives to 3, cleared
master state and retained scene 2. This confirms one Thumper-owned proximity
attack as the damage producer for this C16 ordinary death. It does not establish
all Thumper attacks, phases, defeat/objective behavior, D16 completion or F03
completion.

## Thud arena final-life join

The centrally pinned complete `thud_boss_movie` pair starts from inspected
pristine media in scene 14. Independently retained cycle-neutral arena evidence
shows a natural row-4 boundary at targets 1470/1471: row 4 changes from outside
to inside its squared-distance threshold, speed reverses `-110 -> 110`, ramp
clears `104 -> 0`, and true health changes `3 -> 2`.

Fresh natural and health-only branches share an exact movie-frame-1464 origin.
Changing true health `3 -> 0` changes only main-RAM byte `0x800A6594`. Both
branches then stop at overlay `jal 0x800B4AE0 -> 0x8004A700` (word
`0x0C0129C0`, return `0x800B4AE8`, `$a3=0`). At that entry, a live six-row
census has row 4 as the sole in-threshold row. The natural call returns at
health 2/master state 0; the controlled call returns at health -1/master state
2 while lives remains 0. The matched final boundary retains row-4 speed 110 and
ramp 0.

This confirms one Thud boss-arena contact can enter the resident final-life
selection law. It does not classify the outcome as scripted, special, or
exceptional, and does not complete Thud, Bug Bar, arena, or C16 policy.

## Riverbed Flight actor-contact ordinary-death join

The centrally declared pristine `level_14.sav` anchor is live scene 8, which
the authoritative scene graph maps to `level05\level3b` / Riverbed Flight.
The corrected actor pool begins at `0x8009FD80`; the contact producer is live
slot 5 at `0x800A0014`, not the older Phase-2 discovery index 4. At the exact
damage entry, `$s1=0x800A0014` identifies actor id 37, callback `0x80049E88`
and source backlink `0x80094AC4`. The source record carries actor id 37 and VM
selector 1 (`0x0125`), whose retained E08 owner class remains unclassified.

The exact native invocation is resident proximity-updater
`jal 0x8004B4A0 -> 0x8004A700` (word `0x0C0129C0`, return
`0x8004B4A8`, `$a3=0`). Natural health `0 -> -1` selects master state 2;
the ordinary resident lifecycle then restores health to 4, decrements lives
`3 -> 2`, clears master state and retains scene 8. Passive coverage includes
fatal-health store `0x8004A888`, ordinary-respawn call `0x800500F4` and
respawn writers `0x8005B30C/0x8005B348`.

At the identical pre-contact frame, changing only actor state bit `0x0080`
changes main-RAM byte `0x800A0070` from `0x11` to `0x91`. The branch reaches
the same endpoint frame, cycle, PC and SP while recording no damage-region hit,
no `0x8004B4A0` call, and no respawn-region hit; health/lives remain `0/3`.
This establishes actor-owned contact causation and the ordinary response gate.
It does not identify the actor species, establish a scripted/special death law,
or solve Riverbed Flight motion, chase, objective or transition policy.

## Boundary

This is a confirmed original-game fact for the inspected contact-death,
five-scene natural death-law, Stage-15 boss-context proximity death, Bonus-3
context proximity death, one Thumper actor-owned proximity death, one Thud
row-4 arena final-life path, one Riverbed Flight actor-owned proximity death,
LEVEL02 pit
and title-restart paths. It does not close
broader authored respawn-row policy, natural-lead hazard/actor ownership,
scripted/setpiece/exceptional classes, other bonus contexts, boss damage and
named-enemy causation beyond the bounded Thumper actor and Thud arena path,
F14 flight/chase behavior beyond the unclassified contact,
alternate frontend choices,
explicit native Save/Load, no-card/corrupt-card behavior, or all-stage breadth.
Those boundaries remain with C15,
E10, E14, E15, and E16 as declared
in `config/phase4_lives_gameover.yaml`.

## Evidence

The retained artifact contains load-free save inspection, mounted pristine
media hashes, exact executable slices and instruction words, cycle-neutral
RAM/register/cycle/frame comparisons, and writer access records. See
[[EXP_2026-07-16_phase4_lives_gameover_continue]].
