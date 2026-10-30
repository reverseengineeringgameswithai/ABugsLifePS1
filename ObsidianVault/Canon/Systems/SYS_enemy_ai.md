---
kind: system
id: SYS_enemy_ai
name: Enemy AI — the mover-VM and its programs
aliases: [SYS_enemy_ai, "Enemy AI", "mover VM", "mover-VM"]
status: live_confirmed
confidence: confirmed
source_state: original_game
functions: []
memory: []
tables: []
constants: []
evidence:
  - EXP_2026-07-09_understanding_u3
src_paths: [tools/gen_vm_disasm.py, analysis/vm_programs.json, analysis/vm_programs.md, src_re/enemy_ai_programs.c, asm/hand_written/8004c13c_event_bytecode_interpreter.s]
---

# SYS_enemy_ai

## Purpose
Canon hub for how regular enemies think: every one is driven by a small **bytecode VM** (the "mover-VM",
interpreter [[FUNC_8004C13C_FUNC_8004C13C]]) running a per-enemy program from a resident region. This note ties
the interpreter, the ISA, the disassembled programs, and the aggro model together; deep behavioural detail is
in [[Enemy_AI_movement_programs]] (per-enemy taxonomy + live sweep) and [[Enemy_AI_state_machine]]; spawn /
death live in [[Enemy_spawn_architecture]] / [[SYS_enemy_death_and_permanence]].

## The VM (confirmed)
- **Interpreter** `0x8004C13C` — fetch (signed u16 at the per-actor IP `actor+0x70`) → primary-table index =
  `stream_s16 + 1` → dispatch → advance IP by the handler's operand width → loop; parks on a motion opcode and
  hands off to the phase-2 motion-apply `vm_motion_apply_chase 0x8004C8AC`.
- **Programs** are RESIDENT bytecode in `0x8007745C..0x80077AF6`, indexed by the 13-entry pointer table
  `0x80077AF8` (per-actor IP seeded at spawn). All 13 are disassembled: `analysis/vm_programs.{json,md}`,
  regenerated deterministically by `tools/gen_vm_disasm.py` (operand widths extracted from each handler's own
  `addiu s1,s1,N`; cross-checks the hand decode `src_re/enemy_ai_programs.c`).
- **ISA — 26 of 26 opcodes CONFIRMED** (opcode table `0x8001B2F4`; CALL sub-table `0x8001B35C`). All 26 handler
  functions are named `mover_vm_op<N>_<sem>` in `re_symbols.sym`. **op11 `seek_path_endpoint` is static-confirmed**
  from its complete handler, although it never fired across the traced enemy saves. u3 runtime confirmations (execTrace on pristine enemy
  saves — [[EXP_2026-07-09_understanding_u3]]): **op5** `path_next_waypoint` (mosquito), **op14**
  `anim_clip_load`, **op24** `call_play_sound` (worm strike, operand = sound id); **op9** is `branch_if_s3`
  (byte-corrected from the archived "set-target") and **op25** `cond_powerup_flag` (`0x800A6596` /
  `0x800A6590` bit 0x80) — both pinned in u2-B.

## Aggro model (3 levels, live-falsified — see [[Enemy_AI_movement_programs]])
1. **CHASE** — global motion-phase gate: `flags+0x5c bit 0x2` set AND Flik within an op16 radius → goal swaps
   to Flik's live position. 2. **op17 proximity trigger** — `s3 = dist(Flik) < R`, an op9 branch reacts
   (radii per program, e.g. worm 700, wall_worm/mosquito 1200). 3. **contact ring** — parked on op17/op18 with
   dist² < ~200u → IP += 6 into the strike section (which sets `flags | 0x40`, the berry-tough bit).

**Who sets bit `0x2` — PINNED 2026-08-02, closing the residual `Enemy_AI_movement_programs`
left open ("the gate itself is proven, the setter isn't pinned").** Static disassembly of
`contact_vs_actor_handler` (`0x80058AF8`), found while auditing D09/Redbug:
`0x80059144 lhu v0,0x5c(s2)` → `0x8005914C ori v0,v0,2` → `0x80059150 sh v0,0x5c(s2)` — a
literal OR-bit-2-and-store, inside the hit-tail, BEFORE the HP>0/death branch at
`0x80059154` (so it fires on every landed hit, lethal or not — matches D09's own
non-lethal-hit observations exactly). Gated by three conditions: the legacy `enemy_hp_table`
entry for this actor reads `< 0x78` (120), the actor's own runtime-record backlink
(`+0x80(s2)` → `+0x11`) reads exactly `0x64` (100), and the actor's own id (`+0x00`, reloaded
fresh at `0x800590E8`) is **not** `13` or `15` (grasshopper) — those two ids are excluded
from this path, consistent with grasshopper's chase being documented as "native-assisted"
(a different setter) rather than hit-triggered. Full detail:
`analysis/phase4_d09_redbug_identity.json`'s `STATIC_AUDIT_2026-08-02_who_sets_bit_0x2`.

## Mod levers (documented; no mod built)
op17 radius operands (u16, EXE-editable), op16 chase radii, op2/op3 wait cadence, `flags` bit 0x2, and the
program table `0x80077AF8` (AI swap). All operands are u16 in the resident program region.

## D09 ("cockroach") identified as Redbug — identity + one instance's damage/death, PARTIAL — 2026-08-02

⚠️ **Not Phase-4-DoD closed.** Scored against the roadmap's real 9-item Definition of
Done, this is 0 of 9 met (no scripted oracle, no frontier census, single instance/single
level, no source closure — see the artifact's `DOD_SCORECARD_2026-08-02` block). The row
stays `partial` in `analysis/mechanics_baseline.yaml`, exactly as recorded; the section
title below was corrected from an earlier "live-traced end to end" that overstated it.

**Re-verified 2026-08-02** on a fresh isolated instance after the operator asked whether
this actually meets closure. Caught and fixed a real replay bug (`movie.startPlayback`
without `load_start_state:true` plays against the wrong state — `reproducible:false`
caught it). Reconfirmed identity, HP at frames 437/493/583, and the VM program pointer
exactly. **Corrected one claim**: the CHASE aggro bit flips on the FIRST berry hit
(frame 437), not the second as originally banked. **Found one refinement, not a
contradiction**: death is two-stage — HP reads the `999` sentinel for roughly 20-60
frames, then the record clears to `0` by +70 frames; the original "999" and a later
single-sample "0" were each right for the instant sampled. **Quota non-increment
resolved** (operator: blue-berry damage is a temporary KO path and doesn't spend the
gold-kill quota — already stated in [[SYS_enemy_death_and_permanence]], which this pass
should have checked first). **Follow-up live test, operator-prompted**: skeptical the
species chases at all, the operator asked for a vicinity+throw test. First attempt found
the CHASE bit is transient (clears again later) but could not cleanly confirm or rule out
pursuit movement. **Operator: "go forward with it, exhaust it" — a second attempt, moving
the enemy instead of Flik, CONFIRMED real directional pursuit** on 2 of 2 landed hits
(vs. 0/1 miss, a clean control), following an approach/retreat stand-off pattern rather than
a monotonic charge — see the section below. Full detail:
`ObsidianVault/Experiments/EXP_2026-08-02_phase4_d09_redbug_identity.md`.

Full evidence: `analysis/phase4_d09_redbug_identity.json`. The mechanics baseline's
external/manual-sourced name "cockroach" does not match any of the 12 internal names the
prior cross-level census confirmed (that census covered scenes 1/3/4/5/6/10, never the
city levels) — identified live instead: loaded the row's own fixture
(`movies/Phase4/D09_cockroach_contact_kill.movie.json`), found the actor nearest the
player at the final frame (~1000x closer than the next candidate, HP mid-fight), and
independently cross-checked via its mover-VM instruction pointer, which falls inside
**program index 12 — already labeled `redbug`** in `analysis/vm_programs.md`, written
independently of this pass. **D09 "cockroach" = Redbug (actor id 19).**

Redbug's program shows the wander→chase shape documented above exactly: `random_dir_step`/
`park_seek`/`wait_random` loop, then `chase_radius_scratch[1000]` with the flags-bit-0x4
mask matching the aggro model.

**Damage source corrected from the fixture's own filename.** "contact_kill" implies Flik
body contact; checked the exact recorded input at both HP-change frames and found ZERO
buttons pressed at either moment — widening the search found one `square` (berry throw)
press 35-40 frames before each hit, a plausible projectile flight time. **This is
berry-throw damage** (blue berry, equip index 1, -2 HP/hit off a 6 HP max), not contact.
⚠️ **Corrected 2026-08-02**: the FIRST hit flips `flags+0x5c` bit `0x2` (frame 437,
`0x4041→0x4043`), not the second as originally claimed here — the second hit (frame 493)
only changes HP. ⚠️ **Downgraded 2026-08-02, operator-prompted**: the operator was
skeptical this species has real aggro/chase behavior and asked for a live vicinity+throw
test. Found the bit is **transient, not permanent** — it later reads cleared (`0x5040`,
bit `0x2` gone, a new unidentified bit `0x1000` set instead). A live movement-correlation
test was attempted (position pokes to place Flik close, with `pos`/`prev_pos`/velocity all
written together after catching a bug where writing `pos` alone lets the game's own
`pos = prev + v` integrator snap it back within one tick) but was **not cleanly resolved**:
manual analog navigation proved unreliable (apparent character-relative controls with no
facing readout used to compensate), one window was contaminated by uncleared residual
input, and one Y-coordinate guess dropped Flik into freefall (recovered via a clean reload
before any crash). The cleanest available window (Redbug's own Y, dist 400→19375, chase
flag already expired by that point) showed **increasing**, not decreasing, distance, and
the actor sat motionless for 240- and 540-frame stretches elsewhere in the session
regardless of flag state. **Net: "taking berry damage triggers chase aggro" is DOWNGRADED**
to "sets a flag bit that later clears; whether it produces observable pursuit is untested
cleanly and NOT confirmed" — leaning toward, not establishing, the operator's skepticism.
Full detail: `analysis/phase4_d09_redbug_identity.json`'s `AGGRO_BEHAVIOR_LIVE_TEST_2026-08-02`.

⚠️ **SUPERSEDED the same day, operator: "go forward with it, exhaust it".** A third
isolated instance (port `23497`) fixed the methodology: instead of moving Flik (the source
of every problem above), moved the **Redbug** next to Flik's own already-valid position —
no ground-height risk, no snap-back. A blind `debugger.callFunction` probe at
`ground_height_query` (`0x80037A38`) was tried first and abandoned after it hung and
corrupted the guest (`sp` became `0x000085c0`, `pc` landed in BIOS) — it needs a
sector/plane-record pointer this call didn't supply; recovered via a clean reload rather
than guessing further. **Two landed hits, both showed the same two-phase pattern**: ~40-100
frames of continued *outbound* momentum (the pre-hit heading doesn't cancel instantly),
then a sustained ~100-200 frame accelerating approach straight at Flik (one trial:
dist 49968→18927, `vx` climbing +200→+1058 in Flik's exact direction; the other:
80667→21094 the same way) — far faster and more directional than ordinary wander
(2000-12000 units/40-50 frames elsewhere in this row). **One throw that missed produced
zero directed movement** (a clean no-flag control, 200 frames of plain wander). Once within
roughly 11,000-22,000 units the approach reversed into a retreat — in one trial the CHASE
flag cleared when it did, in the other it stayed set through the retreat — consistent with
an **approach/retreat stand-off oscillation**, not a monotonic charge to melee. **CONFIRMED:
yes, taking berry damage does trigger real directional pursuit.** The prior downgrade is
kept, not deleted, because *why* it was inconclusive is itself the lesson: its observation
windows (60-90 frames) never ran past the outbound-momentum delay this pass found, so it
was reading the wrong phase of the cycle as "no chase." Full detail:
`analysis/phase4_d09_redbug_identity.json`'s `AGGRO_BEHAVIOR_CONFIRMED_2026-08-02_third_attempt`.
Open: why the flag clears on approach sometimes but not others, what triggers the retreat,
whether it ever reaches contact range, and the meaning of flags bit `0x1000`.

⚠️ **Audited the same day** (operator: "do another audit to see if we truly exhausted the
cockroach row"). The three confirmed-chase trials above never actually logged `vm_ip`, so
the chase conclusion had never been cross-checked against the Redbug's own disassembled
program. Checking `analysis/vm_programs.md` shows the program's own `flags_mask`
instructions only ever touch **bit `0x4`**, never bit `0x2` (CHASE) — so bit `0x2` is set by
code *outside* this program (the damage handler), matching the pre-existing architecture
note above ("hands off to the phase-2 motion-apply `vm_motion_apply_chase`"). A **fourth**
isolated trial (port `23498`), sampling `vm_ip` every 10 frames through a full hit→approach→
disengage cycle, found it reads `0x800776A4` (the program's very FIRST `park_seek`, inside
its first wander loop) at **every single sample** — it never advances to the program's own
`chase_radius_scratch` at `0x800776FE`. This rules out the confound the audit set out to
check (that the "chase" could be program-internal wander/anchor-seek coincidentally read as
player-pursuit): the program's IP structurally never reaches that code path, so the
movement must be the separate global override, consistent with genuine player-chase. Not
closed by this: `vm_motion_apply_chase` (`0x8004C8AC`) itself was not traced directly (no
`execTrace` armed — poll-only throughout, per this row's usual practice for a pre-safety
movie) — the attribution is architectural inference plus a negative result (IP not
advancing), not a direct instruction trace.

**The recording does not actually show a kill** — it ends at frame 583 with the Redbug
still alive (HP 2). Took manual control past the recording's end, threw one more berry,
and observed HP go to `999` — the SAME dead-sentinel value already documented for other
enemies, confirming the general death mechanism generalizes to this species. ⚠️
**Refined 2026-08-02**: `999` is a TRANSIENT stage, not the final value — dense re-sampling
found the record clears to HP `0` (and the flags word's top nibble clears too) roughly
50-70 frames after the sentinel is set. A nearby contact-pool entry (action_id 1, recently
spawned) is a plausible but NOT confirmed drop candidate — action_id 1 is shared by many
different ctorTypes (per the E06 kind-classification work), so this is flagged as
suggestive, not proven. The permanent-kill quota `0x800A658E` read 23 immediately before
this kill and stayed 23 for 360 frames after — **RESOLVED, operator-explained 2026-08-02**:
expected, not a bug — blue-berry damage is a temporary KO path and does not spend the
quota, exactly as already stated in [[SYS_enemy_death_and_permanence]] ("red, blue, homing,
mega... do not spend `0x800A658E`"). That existing Canon note should have been checked
before this artifact called the non-increment an open contradiction; recorded as a process
gap, not just a corrected fact.

## D13 (shell_bug) — CHASE bit sets but produces NO movement, correcting an archived categorization — 2026-08-02

Full evidence: `analysis/phase4_d13_shell_bug_armor.json`. Operator: *"i should mention
that these bugs do not have aggro at all. They walk around on a path."* Directly testable
because the D09 audit already pinned the CHASE-bit setter (`0x8005914C`) and its gate
conditions.

**Identity**: fixture `shell_bug.sav`'s two live actors both read `id=18` (shell, per
[[Enemy_spawn_architecture]]'s table) and runtime type-word `0x1712`, an independent
field-level match. `vm_ip` reads `0x80077826`, a `park_path` opcode — structurally
different from Redbug's `park_seek`/`chase_radius_scratch` wander-and-chase loop, despite
both addresses falling inside `analysis/vm_programs.md`'s single auto-generated "redbug"
section (that file only inserted `##` headers at 13 of the actual ~20+ program boundaries
— a real, if minor, generation gap, not a content error).

**Precondition confirmed satisfiable, then tested live**: read the actor's own runtime-
record backlink byte (`+0x80(actor) -> +0x11`) as `0x64` (100) for both instances — the
D09-pinned gate condition IS met, so the bit *can* be set for this species; this was
checked before concluding anything, to rule out a trivial "it can't even try" explanation.
Placed a shell_bug 500 units from Flik (own Y, velocity zeroed, Flik never touched — same
method validated for D09), landed a blue-berry hit (HP `3→1`, flags `0xc041→0xc043`,
CHASE bit confirmed SET), then watched 300 frames. The actor walked away under its own
power for ~90 frames (ordinary path movement, not a reaction), then stopped completely and
stayed at an **exact fixed position for the remaining 210 frames with the CHASE bit still
set the whole time**. A second hit attempt (missed) was followed by another 180 frames of
watching — still frozen.

**CONFIRMED NEGATIVE: no chase/pursuit behavior for shell_bug.** This directly confirms
the operator and **corrects** the archived `Enemy_AI_movement_programs.md` note, which
categorized "shell_bug/canyon_bug" together under "Wander + chase... chase via the global
bit-0x2 gate" — that categorization was made by shared bytecode **address**, not a
behavioral test specific to shell_bug (the note's own sweep table names canyon_bug's
pursuit score explicitly but never tested shell_bug). **Narrowed, not solved**: canyon_bug
was independently confirmed chasing (score `+0.64`) in that same sweep despite documented
sharing of the same program address (`0x800776EC`). A static cross-reference found a
plausible mechanical explanation: shell_bug's own `vm_ip` (`0x80077826`) is labeled
`park_path`, while the address the archived note associates with canyon_bug's own section
of that shared region begins at `0x8007788C`, a `park_seek` opcode — the same
chase-compatible primitive Redbug uses. Different parked opcode within nominally "shared"
bytecode would fully explain divergent chase behavior. **Not live-confirmed against a
verified canyon_bug instance** — a same-day live session intended to test this instead
tested a misidentified LEVEL04 bird enemy by mistake (operator-caught), and this row's
scope was confirmed to be shell_bug specifically, not canyon_bug — see
`analysis/phase4_d13_shell_bug_armor.json`'s `SCOPE_CONFIRMATION_2026-08-02`. canyon_bug
(id 37) does not even share a level with shell_bug (LEVEL01/06/08/10, never LEVEL04),
confirmed by a static scan.

## D13 (shell_bug) — armor mechanic resolved: RED blocked, all other classes work — 2026-08-02

Operator: *"those enemies won't take damage with red berries."* Tested all 5 native berry
classes on fresh reloads of `shell_bug.sav` (isolated instance, media-verified each load):
**red (class 2) — zero damage, confirmed clean over 120 frames. Blue (5), homing (8), gold
(11), and mega (45) all damage normally** (blue/homing: HP `3→1`; gold: the record's `id`
field clears to 0, the permanent-kill finalization shape, distinct from the temporary-KO
shape seen for the others and for D09's Redbug; mega: HP reaches 0 within the window). The
berry-tough bit `0x40` gates **only** the red class — not a time-based "vulnerability
window" as speculated in the row's own prior notes, a fixed per-class exclusion. The exact
gating instruction was searched for in `contact_vs_actor_handler` and not found within the
effort this pass justified (the function has more unrelated special-case branches than
initially assumed) — named as a residual; the behavioral finding stands independent of it.
Full detail: `analysis/phase4_d13_shell_bug_armor.json`.

## Program seeding: type-word HIGH BYTE = program-table index — RESOLVED, 2026-08-02

**Closes a whole-project residual predating this row**: the archived
`Enemy_AI_movement_programs.md` note named it directly — *"Per-level program seeding
(which record field selects the program) — the known GAP-0033 residual."* Found while
identifying the `id=11` actors in `shell_bug.sav` (D13_armored_beetles, operator: "identify
the id=11 actors"). Three live `id=11` instances carried type-words `0x000B`/`0x030B`/
`0x040B` (low byte `0x0B`=11 confirming the id; high bytes `0x00`/`0x03`/`0x04` differing)
and `vm_ip` values `0x8007745C`/`0x800774FC`/`0x8007755C` respectively. Reading the
13-entry program table `0x80077AF8` directly gives entry `0 = 0x8007745C`,
`3 = 0x800774FC`, `4 = 0x8007755C` — an **exact match**, keyed exactly by each actor's own
type-word high byte. Cross-checked against an already-known species: Redbug's type-word
`0x0C13` has high byte `0x0C`=12, and table entry 12 is `0x80077690` — exactly Redbug's own
program start. **The rule holds for 2 species now (Redbug, id=11) and was not yet swept
across the other ~42** — a cheap, high-value follow-up, not done this pass. Does not (yet)
explain species whose high byte exceeds the 13-entry table range (e.g. shell `0x17`=23) —
those must be seeded some other way, or reach a later program via in-bytecode branches
rather than a top-level table index; not resolved here.

## id=11 identified: a large yellow/black-spotted beetle, not shell_bug — 2026-08-02

Visually confirmed via `emulator.captureFrame` (isolated instance, screenshots not
committed — copyrighted game media): moved a live `id=11` actor to within 800 units of
Flik and captured it in-frame, then repeated with a second `id=11` instance (a different
program-table variant) for comparison, then captured both an `id=11` and a `id=18`
(shell_bug) actor in the same frame. Result: `id=11` is a **large beetle with a yellow
shell patterned in black spots, a black/white speckled underside band, a green
thorax/head plate, and blue-purple segmented legs** — visually large and ornate, clearly
distinct from shell_bug's small plain tan/khaki oval shell, confirmed side by side in one
frame. The two `id=11` program-variant instances (table index 0 vs index 4) look
**identical** to each other — the high-byte/program-index variation changes movement
behavior only, not appearance. No internal or external name is established anywhere
checked (`analysis/phase1_kind_actor_census.json` lists id 11 as `unknown_role`;
`config/record_types.yaml`'s actor_record note guesses "movable seed" for id 11 — this
pass's live evidence, a moving HP-bearing mover-VM-driven shelled actor, directly
contradicts that guess, which should be treated as superseded, not authoritative).

⚠️ **SUPERSEDED same day**: this note speculated `id=11` might be D13's primary family
member. A follow-up campaign-wide scan found **130 `id=11` records across 16 of the ~21
campaign RAW files** — essentially everywhere, not a rare special encounter. The operator
separately confirmed D13_armored_beetles' actual scope directly: *"the row is for that
shell bug in LEVEL04"* (chronological Level 7) — the single-level species this page
already documents in the two sections above. **`id=11` and `canyon_bug` (id 37, corrected
by the operator from an earlier live-session misidentification of an unrelated LEVEL04
bird enemy as canyon_bug) are both real, distinct species, confirmed OUT OF SCOPE for
D13.** `canyon_bug` itself was cross-referenced statically: it lives in LEVEL01/06/08/10,
never LEVEL04, so it does not even share a level with shell_bug despite the archived
note's shared-bytecode grouping. Full detail:
`analysis/phase4_d13_shell_bug_armor.json`'s `ID11_IDENTIFIED_2026-08-02` and
`SCOPE_CONFIRMATION_2026-08-02`.

⚠️ **`canyon_bug` renamed**: confirmed the same day as `mite` (D11_mites_grubs' own
subject) — see the "D11 (mite, id=37)" section below. `canyon_bug` was always an
ad-hoc name from this tangent, not the creature's real identity.

## D11 (mite, id=37) — "canyon_bug" identified as the mite from the game manual, combat + respawn timing measured — 2026-08-02

**Identity correction to the two sections above.** `canyon_bug` was always an ad-hoc,
descriptive name coined during the D13 tangent — never the creature's real species name.
Operator, directly: *"i think they're the same bug yeah. Mite was from the manual and it
is accurate to what we were targetting."* **`id=37` (HP 2, vm_ip `0x8007749a`, borrows
spider's own program region) is the mite**, the D11_mites_grubs row's own subject.
`canyon_bug` is retained in earlier notes/artifacts as the historical name used at the
time — not rewritten — but should be read as `mite` going forward.

**Visual confirmation**: the operator confirmed a screenshot (isolated instance,
`canyon_bug.sav`, not committed — copyrighted game media) showing a small orange/yellow
segmented creature with a striped abdomen and a long snout/antenna, standing near Flik on
the Cliffside canyon floor, as the mite. Its exact live-actor RAM identity (which specific
`id=37` instance in that frame) was not pinned via `gpu.pickObject` — the draw call traced
back only to a generic, unnamed low-level GP0-FIFO push primitive (`FUNC_800645c8`), not a
species-specific source. The identification rests on the operator's direct visual
confirmation plus the independently-gathered behavioral match below, not a RAM-level
picking proof.

**Combat and death, live-traced** (`movies/Phase4/Interpreter/mite_kill.json`, 1181
frames, launcher-corrected Interpreter instance): two thrown berries (`square`, no
aim-lock) took the target from hp 2 to 0. Throw 1 activates the thrown-berry gate
(`0x800a6596`) at f127, connects (hp 2→1) at f155. Throw 2 activates at f169, connects
(hp 1→999, the delayed-destroy sentinel) at f203. The actor is fully removed from the live
table (`0x80090748`) at f253 — 50 frames after the second hit registers.

**Respawn, live-measured — a genuinely new finding, not covered by the D13 tangent** (which
never tested it for this species): the SAME actor pointer (`0x800A0AE8` in this fixture)
reappears in the live table with full `hp=2` at **exactly frame 1073** — an **820-frame
gap (≈13.7s)** between death and respawn. This directly confirms the operator's framing,
"it respawns akin to a spider" — mechanically plausible given the mite already shares
spider's own mover-VM program region. D10_spiders' own respawn timer is not yet measured
(still an open item on that row), so this is not yet cross-validated against a spider
value, but is the first hard respawn-timing number for this species family.

**Campaign breadth is already closed, for free**, via the D13 tangent's own static scan
(`analysis/phase4_d13_shell_bug_armor.json`'s `SCOPE_CONFIRMATION_2026-08-02`): mite
(`id=37`) spawns in LEVEL01/06/08/10 only — LEVEL06 is Cliffside Canyon (`scene_id=6`),
where this pass's live work happened, an exact match. Never LEVEL04 (shell_bug's level).

**Type-word closed**: the runtime record backlink (`+0x80`, the same field used to confirm
worm's `id=40`) reads `0x0125` for both live `id=37` instances checked in `canyon_bug.sav` —
agreeing across independently-positioned instances, unlike per-instance fields at other
offsets. Low byte `0x25` = 37 decimal, matching the established "type-word low byte = actor
id" rule exactly.

**Aggro/chase, CONFIRMED NEGATIVE — mirrors shell_bug exactly.** Landed one non-lethal hit
(hp 2→1, the same throw from the combat timeline above) and tracked flags/position for the
following ~150 frames. The CHASE bit (`flags+0x5c` bit `0x2`, the same bit already
documented for Redbug and shell_bug) DOES set on the hit (`0x4011→0x4013`), but the actor's
distance from Flik increases steadily afterward — 53424 units at the hit, 65129 units 45
frames later — moving away, not toward Flik. Same "bit sets, no real pursuit" pattern
already confirmed for shell_bug under D13, now independently reproduced for a second,
unrelated species sharing the mechanism.

**A separate, corrected methodology note for this same row**: two much older fixtures,
`D11_grub_contact_kill.movie.json` and `D11_mite_contact_kill.movie.json`, turn out not to
show a grub or a mite at all. The "grub" movie's kill target is `id=12`, already
Canon-confirmed as the [[#D12 (earthworm, id=12)|D12 earthworm]] — and an
initial working hypothesis this pass, that the earthworm "poked" Flik (from a timing
correlation with a flags change), is WRONG and retracted: that page already states the
earthworm's own program has no strike mechanic at all. The "mite" movie's actors (`id=11`,
`id=37`, `id=30`) are all pre-existing, already-identified species (the large beetle, this
row's own mite, and the D17 bird respectively) — none of it is fresh D11 evidence. Both
fixtures are left alone (not deleted, not renamed) but should not be cited as D11 evidence
going forward; `mite_kill.json`/`.sav` is the real fixture for this row.

Full evidence: `analysis/phase4_d11_mite.json`,
`ObsidianVault/Experiments/EXP_2026-08-02_phase4_d11_mite.md`.

## D12 (worm, id=40) — armor confirmed a SECOND species, stationary-anchored, and the STRIKE mechanic measured live — 2026-08-02

Full evidence: `analysis/phase4_d12_worm_id40.json`. D12_centipedes_earthworms is the
only row in the whole baseline touching worm/earthworm/centipede at all; the operator
directed focus specifically to actor `id=40` ("worm"), confirmed live in `worm.sav`
(identity: `id=40`, runtime type-word `0x2528`, matching [[Enemy_spawn_architecture]]'s
table exactly).

**Armor confirmed a second time, exact match to D13.** Operator, unprompted: *"the worm
has the same armor that red berries won't work against it, it will bounce off of it."*
Tested all 5 native berry classes on fresh reloads: **red — zero damage** (HP stayed 8);
**blue/homing — `-2`; gold — `-4`; mega — `-3`** — an exact match to the already-documented
generic hit-tail switch (class 0/12→`-2`, 127→`-4`, 128→`-3`), now confirmed for a second
berry-tough species. The berry-tough bit `0x40` gates only red, generally, not just for
shell_bug.

**Stationary confirmed, and more strongly anchored than shell_bug.** Watched 240 frames
with no interaction: position never changed once despite `vm_ip` actively cycling every
~60 frames — matches the archived note's "Stationary (zero movement): worm, pill_bug,
wall_worm" sweep result, now directly confirmed rather than only inferred. A position poke
(the same method safe for shell_bug/Redbug) **snapped back to the worm's own anchor within
one 30-frame check** — worm actively enforces its anchor, unlike shell_bug which tolerated
repositioning.

**STRIKE mechanic measured live for the first time.** Since the worm resists
repositioning, moved Flik instead (own validated Y, `pos`+`prev_pos`+velocity written
together). Placed 400 units from the worm (inside the documented 700-unit radius) and
sampled every 5 frames: **Flik's true health dropped `4→3`** within 5 frames, and Flik was
simultaneously launched away by a strong knockback impulse, reaching 12,000+ units of
separation within 30 frames. **This explains a repeated "unexplained drift" observed in
earlier sessions this same day (D09, D13) — it was knockback from a strike, not a bug or
residual-physics artifact.** The worm's own `hp` stayed exactly `8` (not a mutual-damage
contact). Only one strike landed before the knockback carried Flik out of range.

**Campaign breadth**: static scan confirms worm (`id=40`) in 5 levels — `LEVEL01`(3),
`LEVEL03`(2), `LEVEL07`(4, coexisting with D13's shell_bug in the same disc directory),
`LEVEL08`(4), `LEVEL10`(4) — 15 records total, zero variants. The row's own namesake,
earthworm (`id=12`), is confined to `LEVEL03` only (11 records, zero variants) — a
single-level species like shell_bug; see its own section below for the later armor/strike
sweep.

**STRIKE mechanism traced to its native call, no fresh disassembly needed.** The bytecode
around the live-observed `vm_ip` values (`analysis/vm_programs.md:392-411`) reads
`player_proximity[700]` → (in range) → `flags_mask` sets `+0x5c` bit `0x40` →
`call_native[8]` → native `0x80057b84`, then loops back into the wander cycle. A SECOND,
near-identical window exists later in the same program (`player_proximity[1200]` → same
`call_native` → same native) — the worm has two proximity-strike windows per cycle, not
one. The native itself was **already decompiled in this repo** under a name that, in
hindsight, matches exactly what was observed live:
`src/main/80057b84_vm_native_aimed_drop_spawn.c` (`vm_native_aimed_drop_spawn`, single
caller `0x8004c644` = the VM's own `call_native` dispatcher, per
`analysis/phase3_call_graph.json`). It spawns a burst of 8 objects cycling kinds `21/22/23`
at the **caller's own position** via `spawn_drop` (`0x80059e44`, the same function used for
gold-berry/pickup drops), then — **only when the caller's `id == 40`, hard-coded** — aims
that burst's facing at the player via an atan2-style heading, instead of the generic
descriptor-byte facing every other caller gets. **So the STRIKE is not a direct
`contact_vs_actor_handler` hit** (the function searched twice already this session for the
berry-tough gate PC, both times more tangled than expected) — it is a distinct code path:
an aimed spawn of drop-type objects. The observed 1-point true-health hit + knockback to
Flik almost certainly comes from Flik's own contact with one of those spawned objects, not
from the worm's own record directly. **Not yet traced**: the handler that applies
damage/knockback from a kind-21/22/23 object on contact, and those kinds' own visual
identity. Full detail: `analysis/phase4_d12_worm_id40.json`'s
`STRIKE_MECHANISM_STATIC_TRACE_2026-08-02`.

**In-session respawn — ⚠️ RETRACTED and corrected same day.** A first test killed a fresh
`worm.sav` with four blue-berry hits and watched 4000 frames with Flik stationary: `hp`
stayed `0` throughout, no revival. That was banked as a general negative result, then
retracted after the operator supplied direct gameplay knowledge (it respawns, but only once
Flik actually leaves and returns) and a live re-test with Flik genuinely walking away
confirmed a full reset — `hp` back to `8`, `id` still `40`, `vm_ip` landing near the mover
program's own start. The mechanism was then ASM-traced to a previously-undocumented
reinstantiate-from-spawn-template routine, with real open residuals (its exact trigger
condition, and a contradiction in the distance-admission logic). Full detail, including the
retraction and every caveat: `analysis/phase4_d12_worm_id40.json`'s
`RESPAWN_TEST_2026-08-02_RETRACTED` and `RESPAWN_MECHANISM_2026-08-02`; cross-cutting
summary on [[SYS_enemy_death_and_permanence]].

## D12 (wall_worm, id=41) — armor matches, STRIKE does NOT reproduce despite shared bytecode — 2026-08-02

Full evidence: `analysis/phase4_d12_worm_id40.json`'s `WALL_WORM_ID41_SWEEP_2026-08-02`.
Directed next after worm was closed out, to check whether the id==40-hardcoded aim
special-case found in `vm_native_aimed_drop_spawn` means wall_worm behaves differently.

**Identity confirmed**: `id=41`, matching `Enemy_spawn_architecture.md`'s table
(`wall_worm 0x2629 -> 41`). Initial state (hp=8, flags=`0x4045`) is bit-identical to worm's
own, and `vm_ip` on load (`0x80077aa2`) sits inside the exact same shared bytecode block
worm executes — confirmed live, not just inferred from the archived shared-bytecode
grouping. **Stationary confirmed** (240 frames, zero movement). **Armor matches exactly**:
blue `-2`, homing `-2`, gold `-4`, mega `-3` — a 4th berry-tough-family instance of the
same hit-tail switch. Red showed no hp change across 6 attempts, consistent with the
established rule, but an attempt to independently verify the throw actually connected (an
exec-trace watch on the throw dispatch `0x80047170`) returned 0 hits even on a fresh
5-trial re-check — inconclusive on its own, so this result is flagged with that caveat
rather than claimed as a clean third re-proof the way worm's and shell_bug's were.

**STRIKE tested at two distances, CONFIRMED NEGATIVE — a real behavioral divergence.**
Moved Flik to 400 units (well inside both the 700 and 1200 unit proximity radii), watched
400 frames / 2 full loop cycles: no strike. Moved to 80 units (near point-blank), watched
600 frames / ~2.5 loop cycles: still no strike. Critically, `vm_ip` was directly observed
sitting AT the proximity-check instruction itself (`0x80077a70`) and the next sample had
already advanced past it without taking the in-range branch — the check was *reached and
evaluated false*, not just never reached. Since both actors run identical bytecode with the
same baked-in radius literals, the most likely explanation is that wall_worm's true
render/hitbox position doesn't equal its `+0x28` anchor field the way worm's does — plausible
for an actor that spends part of its cycle embedded in a wall — but this was **not confirmed
live**, only proposed as the next hop. Either way, the behavioral result stands on its own:
wall_worm does not strike Flik under conditions that reliably strike worm within ~30 frames.

## D12 ("earthworm", id=12) — the row's own namesake, no strike mechanic — 2026-08-02

Full evidence: `analysis/phase4_d12_worm_id40.json`'s `EARTHWORM_ID12_SWEEP_2026-08-02`. Last
untested species in the family after worm and wall_worm were both closed out.

⚠️ **`id=12` is NOT an earthworm — corrected the same day, see the section below.** The name
came from an early, never-visually-verified static census table. It IS the grub,
D11_mites_grubs' own subject. This section is left as historical record (it was accurate
static/behavioral work, just under the wrong species name); the identity correction and the
completed armor sweep are in the next section.

**Identity and hp**: `id=12` confirmed live (`Enemy_spawn_architecture.md`: `earthworm
0x060C -> 12` — this table entry's own name is the thing that turned out wrong). Max hp is
`1` — a single successful hit of any working class kills it outright, too little HP to
distinguish per-class damage amounts.

**No STRIKE mechanic, confirmed statically for free.** `analysis/vm_programs.md` already has
a dedicated labeled section, `## earthworm @ 0x800775c8`: a plain
`wait_random → random_dir_step → park_seek → jump_back` wander loop — no
`player_proximity` opcode and no `call_native`, unlike worm/wall_worm's shared ambush
block. This actor does not run that program at all and, on this read, has no
proximity-triggered strike.

**Armor: homing confirmed live at the time, the other four classes relied on operator
testimony only — since independently closed, see the section below.** A first attempt used
the fixed ~1.6s post-throw wait that worked for every other species in this row and found
0/6 landed for homing — the operator corrected this: homing *does* connect, it just takes a
couple of real seconds to travel. Re-run with a longer watch confirmed it: hit landed at
+2.0s, hp `1 → 0`. Red/blue/gold/mega were not independently live-confirmed at the time —
even from the fixture's own default position (visually confirmed via a screenshot to already
have Flik standing right next to the target), straight-aimed throws didn't land, which the
operator explained as a facing/aim-cone problem specific to non-homing throws, not a
damage-blocking mechanic. "There is no armour for the little earthworms" is the operator's
own direct real-gameplay observation, banked at the time as testimony — since independently
confirmed live for all 5 classes, see below.

**Method lesson, worth keeping in mind for future position math**: an attempted
reposition (offsetting Flik via this actor's own `+0x28/2c/30` anchor field) produced a
visually wrong placement — caught by the operator watching the live emulator window, not by
anything in the numbers. The anchor field is evidently NOT safely comparable to Flik's own
`0x800A6500` coordinate space (a ~44,000-unit Y mismatch against a screenshot showing them
standing on the same visible ground) — flagged as a standing caution, not just a one-off
mistake.

## D11/D12 (grub, id=12) — "earthworm" corrected to grub, full 5-class armor sweep closed — 2026-08-02

Full evidence: `analysis/phase4_d12_worm_id40.json`'s `GRUB_IDENTITY_AND_FULL_ARMOR_SWEEP_2026-08-02`
and `analysis/phase4_d11_mite.json`'s `GRUB_HALF_RESOLVED_2026-08-02`. Same day as the D11
mite work above; operator: *"if the grubs (previously worked on as earthworms) aren't
exhausted then go for it."*

**Identity correction.** `id=12` is not an earthworm. Loaded `earthworm.sav` directly,
captured a live frame with Flik in the fixture's own already-good default position next to
it: short and plump, a large rounded head, a big eye, small ear-like features, a dark
segmented ridge trailing behind it. Operator: *"yes that's a grub, we already established
this."* The "earthworm" name traces to an early static census table
(`Enemy_spawn_architecture.md`'s type-word list) that was never independently visually
verified until now — the same failure mode as `canyon_bug`→mite above, on a different
species. `id=12` (grub) properly belongs to D11_mites_grubs' own scope; the row ID/name
`D12_centipedes_earthworms` is left as-is (a rename is a larger structural decision), the
mismatch is simply flagged here.

**A testing-method bug, not just a facing problem, explains part of the earlier "armor
testimony only" result.** `emulator.pressButton` with a `seconds` duration auto-pauses the
emulator once its own hold window elapses — a caller must issue a fresh `debugger.resume`
*after* it returns, or all subsequent polling reads a frozen, paused game (confirmed live:
the thrown-berry gate `0x800a6596` never changed across 4 continuous seconds of polling
until this fix was applied). This is a general method note for any live combat test in this
project using `pressButton` with a manual post-press polling loop, not specific to this
species.

**Facing, once the method bug was fixed**: straight (non-homing) throws still missed from
the default orientation. A brief `left` d-pad tap (0.15s) immediately before throwing turns
Flik enough to connect reliably. Homing-type throws (green, and mega/purple — mega is ALSO
homing per the established kind table) need the *opposite*: thrown from the default
orientation with NO turn. Adding the turn before a mega throw caused it to whiff even after
a 5-second wait; removing the turn let it connect at ~1.0-1.5s, in the same ballpark as
green/homing's already-confirmed ~2.0s. Consistent with homing using its own
acquisition-based targeting that a manual facing adjustment disrupts.

**Full armor sweep, all 5 classes independently live-confirmed**: green/homing (already
confirmed prior pass), red-or-default (marker 0, with the turn), blue (marker 1, with the
turn), gold (marker 3, with the turn), and mega/purple-homing (marker 4, default
orientation) — every class connects and kills this hp=1 actor. **No armor at all**, unlike
shell_bug/worm/wall_worm, which all specifically block the red class at 0 damage. This
upgrades the operator's own testimony ("no armour for the little earthworms") from
testimony-only to independently live-verified for every class. One naming caveat: marker
value 0 was assumed to be "red" by elimination against the established pickup-kind table
(`0x21/22/23/24` = green/gold/blue/purple, leaving `0x20`/marker-0 as the remaining
default/red slot) — not independently re-verified this pass, though the behavioral finding
(every tested marker connects) holds regardless of that specific class name.

**Aggro/chase, CONFIRMED POSITIVE — a genuine behavioral divergence from mite.** `hp=1`
makes a single hit lethal, so a test-only HP poke (`+0x6e`, `1→8`) let the actor survive a
hit for observation — flagged explicitly as a test intervention, not natural gameplay.
Landed one throw, then polled position and flags against Flik's stationary position for
~6 real seconds. The CHASE bit (`flags+0x5c` bit `0x2`, the same mechanism confirmed for
Redbug/shell_bug/mite) sets on the hit (`0x4001→0x4003`), and this time the position traces
a genuine **approach-then-retreat arc**: distance to Flik falls from 15883 units at the hit
to a minimum of ~4856 units around t=3.0-3.3s, then rises back to 21657 by t=5.7s — the same
"approach/retreat stand-off oscillation" shape already documented for D09 Redbug, not a
monotonic charge. A second flag transition (`0x4003→0x5001`, losing bit `0x2`, gaining bit
`0x1000`) happens mid-arc (~t=1.2s) while the movement continues uninterrupted — the
persistent pursuit state more likely tracks bit `0x1000` than the initial-hit bit `0x2`, not
independently confirmed. **Grub chases; mite and shell_bug don't**, despite all three
sharing the same CHASE-bit-on-hit mechanism.

### Exhaustion assessment — D11 mites/grubs, 2026-08-02

**BOUNDED PARTIAL.** Identity, combat/death, armor (grub's full 5-class sweep, no armor at
all), respawn timing (mite, 820 frames/≈13.7s), and aggro/chase (both species, a genuine
divergence — grub chases like Redbug, mite doesn't like shell_bug) are all answered and
cross-verified. What remains — grub's own respawn timer, whether mite's respawn is
fixed-or-random, the exact identity of flag bit `0x1000`, whether a genuine separate
"earthworm" exists at all, a campaign-breadth re-stamp for grub under its corrected name,
source closure, cross-system audio/HUD — is either repetitive measurement with a
predictable outcome, speculation with no concrete lead, routine bookkeeping over
already-known data, or standard last-mile completeness every row carries. None of it is a
live open question that would change what's already banked. Full reasoning:
`analysis/phase4_d11_mite.json`'s `EXHAUSTION_ASSESSMENT_2026-08-02`. Both rows
(`D11_mites_grubs`, `D12_centipedes_earthworms`) remain `partial`, not `solved` — this note
documents why work paused, it does not upgrade status.

## D15 (daddy long legs, id=17) — "huge_spider" is the row's own subject; the web attack is CONFIRMED LIVE — 2026-08-02

Full evidence: `analysis/phase4_d15_daddy_long_legs.json`. A pre-existing, purpose-recorded
fixture (`movies/Phase4/D15_daddy_long_legs_contact_kill.movie.json`, 416 frames) existed
but had never been indexed (registry showed `fixture_have: []`).

**Identity**: the fixture's kill target is `id=17` — already established elsewhere as
"huge_spider" (`0x0b11`, per `Enemy_spawn_architecture.md`'s archived type-word table),
confirmed again live via the same runtime backlink method used for worm/mite. A second
untouched actor in the same fixture, `id=6` (Horsefly), belongs to D08_flies and is
unrelated. Captured a live frame near `id=17`: a distinctive silhouette with extremely
long, thin, spindly red legs radiating from a small green/purple body. Operator, directly:
*"'huge_spider' is daddy long legs, fyi."* Same naming-gap pattern as mite/canyon_bug and
grub/earthworm found earlier the same day — an internal census name that doesn't match the
common species name — but without a wrong-species mixup this time.

**No strike mechanic in ONE specific program region — scope corrected below.**
`analysis/vm_programs.md` has a dedicated labeled section, `## huge_spider @ 0x80077674`: a
plain wander loop (`set_byte_params → anim_clip_load → wait_random → random_dir_step →
park_seek → jump_back → park_end`) — no `player_proximity` opcode, no `call_native`. This
was originally read as answering the row's own "web projectile, range behavior" scope item
in full; it does not — see the correction below.

**Combat, live-traced**: two thrown blue-class berries (confirmed live via the berry marker
byte) kill it, `-2`/hit matching the generic hit-tail blue/homing damage amount used
elsewhere. Gate activates f286, connects (hp 4→2) f318; gate activates f328, connects
(hp 2→999) f352; removed from the live table at exactly f400.

**⚠️ Aggro/chase claim RETRACTED — the web attack is real and unobserved, not ruled out.**
The original test watched flags and position across a hit landed from ~53000+ units away
(the only distance the combat fixture ever reaches) and found zero reaction, banked as
"CONFIRMED NEGATIVE." Operator, directly: *"surely it has aggro since it shoots a web?"* —
correct: a test that never brings Flik anywhere near attack range cannot rule out an attack.
A follow-up used an operator-supplied save from their own DuckStation savestates directory
(copied, not moved, to `movies/Phase4/D15_daddy_long_legs_web_attack.sav`) described as
showing "Flik in the vicinity of the daddy long legs. Shortly after, the spider turns to
Flik and throws a web at him." That save is `scene_id=1` (chronological Level 2) — a
**different level** from the combat fixture's `scene_id=5` (Level 8), itself new campaign-
breadth information (this species spawns in at least 2 levels). Careful position-based
approaches (learning from one bad teleport that dropped Flik through unstreamed floor
geometry — a standing project hazard, not species behavior) got a candidate actor (`id=14`,
the only one of 5 live actors in that save with an active `player_proximity[1200]` opcode,
in the `## mosquito @ 0x800775e4` program) down to ~9000-20000 units without triggering an
attack before it wandered off on its own path again. Whether `id=14` is even the right
target actor was not resolved. Operator ended the investigation here ("daddylonglegs in ABL
is fine") rather than continue guessing blind.

**Net at the time**: the row's real combat/aggro behavior — specifically the ranged web
attack — remained genuinely open. What stood was narrower than originally claimed: no
reaction was observed in one specific far-range fixture, and no `player_proximity`/
`call_native` exists in one specific program address (`0x80077674`) — neither claim
generalized to "this species has no attack." Full detail:
`analysis/phase4_d15_daddy_long_legs.json`'s `AGGRO_CORRECTION_2026-08-02`.

**✅ Web attack CONFIRMED LIVE — the correction was right.** The operator recorded a proper
movie of the encounter (`movies/Phase4/Interpreter/DaddyLongLegs.movie.json`, 1448 frames,
same `scene_id=5` as the original combat fixture, confirming this really is `id=17`). Flik's
health drops in three separate steps — f312 (4→3, distance **73286** units), f604 (3→2,
distance **48405** units), f798 (2→1, distance **14245** units, the SAME frame the target's
flags gain bit `0x1000` seen transiently during an earlier teleport experiment) — while the
target's own hp stays at 4 (undamaged) throughout. These distances are one to two orders of
magnitude beyond any contact range: this is unambiguously a ranged attack, firing roughly
190-290 frames apart across a wide range band (~14000-77000 units), not a tight fixed-radius
trigger the way worm's 700/1200-unit strike windows are. Flik then counter-attacks (gate=3,
multiple berries in flight) — first hit f1280-1282 (hp 4→2), second f1340-1342 (hp 2→999),
removed from the live table at exactly f1390.

**This fully reverses the AGGRO_2026-08-02 finding**, not just leaves it retracted — the
species does have a real, confirmed ranged attack. What remains open: the exact trigger
mechanism (timer vs. proximity vs. a hard-coded per-id check, paralleling how worm's real
strike lives in a `call_native` outside its simple wander program — not traced to an
instruction here, only inferred behaviorally from three health-drop events); whether the web
is a directly observable spawned/tracked object; why flags bit `0x1000` only appears at the
third hit, not the first two. Full detail: `analysis/phase4_d15_daddy_long_legs.json`'s
`WEB_ATTACK_CONFIRMED_2026-08-02`.

**✅ Full producer chain traced live — 2026-08-02, INCLUDING a self-caught correction.**
Following the operator's "keep drilling down until you deem it substantially exhausted,"
the whole chain was traced end-to-end. Damage side closes against already-Canon code: the
health-decrement write (`0x8004a888`, inside [[FUNC_8004A700]]) is called from
`0x80058A48`, inside the already-decompiled [[FUNC_800586B0]] (`contact_walker`,
`src_re/contact_walker_800586b0.c`), which dispatches on the contact-pool record's own
`action_id=118` — a value that file's own header comment already flagged as aliasing to
the documented `WALKER_CASE_UNK_52` case, just never before connected to "this is the D15
web attack." The record was confirmed live as a genuinely MOVING/tracked object (closing
distance to Flik across consecutive frames before each hit registers), answering one of
`WEB_ATTACK_CONFIRMED`'s own open questions.

A first attempt at the spawn side (breakpoint at `FUNC_80059E44`'s entry, `$ra` trace)
pointed at a call inside [[FUNC_800563D4_actor_skinned_update]] (`ctorType=49`) — this was
**verified against the metadata table and found WRONG**: table row 49 holds `action_id=1`,
not 118. That call site is real and does something else (documented on its own page as a
ruled-out D15 lead, kept there so it isn't re-chased). The real chain: the write PC
(`0x8005a1d8`) is actually inside a separate sibling allocator (`0x8005A0E0`, already
partially Canon as [[FUNC_80059E44]]'s "explicit constructor" variant, also used by the
unrelated berry-throw system), called from [[FUNC_8004A2B0_aimed_object_spawn_sfx]] — a
380-byte function that already had a static name and rationale
(`analysis/naming/u2_batch04.json`: "spawns a contact object with computed heading +
sound") but no prior Canon page or live-confirmed gameplay meaning. It computes the angle
to Flik via an atan2 helper, runs a randomized per-candidate attack cooldown (`[40,103]`
frames), spawns the web via a FIXED metadata pointer (`0x80079da4`, confirmed live:
`action_id=118`, `active_type=60`), and immediately fires SFX id `25` — very likely the
web's own sound effect, a direct answer to the row's cross-system/audio gap.

The function is reached only via an indirect (`jalr`) call, matching
`analysis/phase3_fn_ptr_fields.json`'s pre-existing census of `actor_record+0x7C`: a
function-pointer callback field, 9 distinct handlers, 1286 live instances censused.
`aimed_object_spawn_sfx` accounts for 68 of them; `mosquito_species_callback` (D07's own
confirmed callback) is a sibling value in the same slot. This is the SAME optional
per-species callback architecture D07_mosquitoes independently confirmed the same
session — species-specificity comes from which function pointer gets assigned to an
actor's own `+0x7C` at spawn time, not a hard-coded id branch. **CONFIRMED LIVE
2026-08-03**: id=17's own live actor record (`0x800a0ae8`) reads `+0x7C = 0x8004A2B0`
exactly at all 6 frames sampled across the full movie replay, in a fresh isolated
instance that avoided the movie-replay non-determinism that blocked the first two
attempts (a long-lived, many-times-reloaded instance). Cross-validated against the
record's own hp/flags transitions matching the already-documented combat timeline.
Full detail and the complete false-lead/correction trail:
`analysis/phase4_d15_daddy_long_legs.json`'s `PRODUCER_CHAIN_TRACED_2026-08-02` and
`CALLBACK_CONFIRMED_LIVE_2026-08-03`.

## D20 (Hopper, final boss) — identity corrected + white-berry producer chain traced — 2026-08-02

Full evidence: `analysis/phase4_d20_hopper.json`. Picked as the next unresolved row,
avoiding D19_molt (another agent's row).

**Identity correction.** `ObsidianVault/Archive/Superseded/Systems_Enemy_AI_state_machine.md`
claims Hopper "REUSES the chaser AI... Actor = chaser slot `0x80095358`" — the EXACT same
claim shape that file's own later Thumper correction (residual #5) found wrong:
`0x80095358` is the camera, not a boss actor. The Hopper section predates that fix
(2026-06-22 vs. 2026-07-03) and was never revisited. Live re-scan of the chunk-31 live
actor table (`0x8009FE04`, stride `0x84` — the same base already correct for Thumper)
found 4 distinct ids in the canyon-showdown scene: `id=11` (movable seed, already-Canon
generic class), `id=15` (15 undifferentiated background instances, uniform hp=6 — not a
boss), `id=30` (the already-Canon D17 bird boss), and **`id=22`** — singular, genuinely
live/moving, at a plausible distance from Flik in a save captured mid white-berry-throw,
matching an on-screen boss-shaped figure. High confidence, not yet `gpu.pickObject`-closed
(same known vertex-buffer-only limitation already documented for Thumper's own ID).

**White-berry producer chain, self-recorded and traced live.** Operator confirmed a fresh
Interpreter movie would be needed for any instrumented work; rather than requiring a
manual playthrough, the existing `hopper_throwing_white_berry.sav` already sits at the
moment Hopper commits to the throw, so a new movie was self-recorded from that anchor
(`movie.startRecording` + `load_start_state:true`, no navigation needed) —
`movies/Phase4/Interpreter/Hopper_white_berry_death.movie.json` (642 frames, v4).

Over the captured sequence, `id=22` closed distance on Flik from ~40,000 to ~8,000 units
(confirmed pursuit) while Flik took 3 hits and died. **Damage side closes against
already-Canon code**: two hits came from `0x80058A48` — the SAME `contact_walker`
(`FUNC_800586B0`) caller D15's web attack uses — and a third, landing one frame after the
first, came from `0x8004B4A0` (an already-Canon direct-contact resolver): a projectile hit
and a body-contact hit within 2 frames of each other, not one mechanism. **Spawn side**
traces the projectile (contact-pool `action_id=2`, confirmed via closing-distance-from-
below arc behavior identical to D15's own methodology) to the SAME sibling contact-
allocator (`0x8005A0E0`) D15's web and the unrelated berry-throw system already use —
confirming that allocator is a genuinely generic, cross-species, cross-system utility.

**The spawn caller is overlay-resident, in the SAME unresolved region flagged for
Thumper.** The call site (`0x800b46d4`) sits inside the boss combat overlay
(`~0x800b3c04-0x800d1570`) — exactly the range the archived Thumper section names as OPEN
("all three live in the boss COMBAT OVERLAY `~0x800b4xxx`"). Two more overlay-resident
spawn sites turned up incidentally: `0x800b4934` (action_id 50, likely a landing/hop-dust
effect) and `0x800b4a40` (action_id 52, generic ambient dust). `transferLog.resolve`
couldn't identify the overlay file (loaded before this session's instance connected, from
a save rather than a live boot) and `functionBounds` returned a 121,200-byte unmapped
merged region — closing this needs a cold-boot capture with `transferLog` armed before the
overlay loads.

**Still open**: the overlay's own file identity and internal function boundaries; barrier/
retreat state; the exact finale-trigger instruction; whether `+0x6e` is real depletable HP
(Flik died from Hopper's attacks before this could be tested); campaign breadth beyond
stage 15; source closure; audio. Full detail: `analysis/phase4_d20_hopper.json`.

**Operator-recorded full fight — bird-nest finale located, 2026-08-02.** The operator
recorded an independent 16,711-frame Interpreter movie (`movies/Phase4/Interpreter/
D20.movie.json`) through to an actual "level complete" screen — confirming the recording
captures Hopper's real defeat, not just combat. Lives drop from 9 to 7 across the
recording; operator, directly: *"the death / damages on my part was poor gameplay,
nothing to do with solving Hopper"* — noted for completeness, not a mechanic finding. A
poll-only survey (no instrumentation armed) found a screenshot at movie-relative frame
~16100 showing a distinct scripted cinematic — a large red/orange bird in a nest, wings
extended, with a smaller creature — almost certainly the bird-eats-Hopper finale the
archived note names as never decoded ("the bird setpiece `FUNC_8004DD98`... this would
confirm it in its real Hopper context"); `scene_id` (`0x80082504`) transitions from 15 to
0 somewhere in frames 16100-16300, narrowed no further this pass (movies don't support
rewinding, so a tighter bisection needs a fresh reload); by frame ~16700 the
level-complete screen is up. This fixture likely closes several remaining open items in
one follow-up pass — the exact finale trigger (now narrowed to a ~200-frame window), its
connection to `id=22`'s own state at defeat (by analogy to Thumper's `0x80090bee`/
`0x80090bec` defeat-flag pair), and the ending transition — but was surveyed, not yet
instrumented. **The Atta chase is confirmed OUT of this row's scope** — operator,
directly: *"Atta is not in this stage as that is LEVEL 14, this was only level 15."* Atta
belongs to Stage 14 (`F14_riverbed_flight`'s own subject), not D20's stage-15
canyon-showdown material. Full detail: `analysis/phase4_d20_hopper.json`'s
`OPERATOR_RECORDED_FULL_FIGHT_2026-08-02`.

**✅ Finale trigger traced to an exact instruction — 2026-08-02.** Reloaded
`D20.movie.json` fresh and bisected the 16100-16300 window forward-only (movies can't
rewind) down to a 5-frame range, then armed `accessLog` on `id=22`'s own hp/flags/id
fields, on Thumper's own defeat-flag pair (`0x80090bee`/`0x80090bec`, to directly test
reuse), and on `scene_id` itself. Found the exact write: absolute frame 36166
(movie-relative 16166), PC `0x800503ac`, `sw zero, 0x2504(at)`, `scene_id` 15→0. The
enclosing function (`0x8005038c-0x800503fc`) is already fully Canon —
[[FUNC_8005038C_scene_setup_and_load]] — a GENERIC, whole-game scene-transition
dispatcher, not anything Hopper- or boss-specific, confirming Hopper's defeat routes
through the same machinery as any ordinary scene change. That function's own documented
callers are `main_shell_state_machine`, `scene_flow_dispatcher`, and
`fmv_sequence_completion_check` — the last is the strongest candidate for the actual
trigger (it already sums a 16-entry completion-flag array and, on a specific total, calls
`fmv_bin_load` then `scene_setup_and_load`), but which of the three fired this specific
call was not confirmed this pass. `id=22`'s own hp and id fields received zero writes
across the whole ~30-frame instrumented window — Hopper's record is not despawned or
health-modified at defeat, and does NOT reuse Thumper's specific defeat-flag pair (a
clean negative result). Full detail: `analysis/phase4_d20_hopper.json`'s
`FINALE_TRIGGER_TRACED_2026-08-02`.

**✅ Aggro/chase mechanism confirmed — 2026-08-03, and a self-correction.** Operator,
directly: *"did we exhaust his aggro nature where he chases Flik?"* The honest answer at
that point was no — only the RESULT of chasing (closing distance) had been confirmed,
never the driver or gate. That prior answer of mine ("no aggro flag/gate found") was
wrong — not because the mechanism doesn't exist, but because it hadn't been checked
deeply enough. `src_re/enemy_ai_programs.c` (already committed 2026-07-03, a month before
this session) fully documents and live-falsification-tests the GLOBAL chase mechanism
every regular enemy uses: the shared mover-VM's motion-apply phase (`0x8004c8ac`+) has a
chase gate at `0x8004c930` — if actor flags (`+0x5c`) bit `0x2` is set and Flik is within
a per-object radius, the motion goal swaps to Flik's live position. (Suppressing that bit
on a live chasing spider flipped its pursuit score `+0.93 → −0.89` — already proven, not
new this pass.)

Live-traced `id=22`'s own position writes (X at `0x8004cd64`, Z at `0x8004cdcc`, both
inside `FUNC_8004C13C`, the shared mover-VM) during the confirmed-pursuit window of
`movies/Phase4/Interpreter/Hopper_white_berry_death.movie.json` — NOT the camera function
(`FUNC_8004DF18`) the archived note wrongly pointed at. Checked `id=22`'s own flags bit
`0x2` at 7 sampled frames across that window: **set at every single sample**, correlating
with distance oscillating 8,261–46,299 units as he closes to throwing range and backs
off. Cross-checked against the earlier finale-trigger trace's own flags reads near
defeat: bit `0x2` reads **clear** there — his chase gate disengages before the scripted
cinematic. Hopper's own program pointer (`actor+0x70`) landed inside a long,
previously-unattributed block of `analysis/vm_programs.md` (past the last named header,
`redbug @ 0x80077690`) — a generic wander loop, not yet walked start-to-end or given a
species name.

This also corrected a **stale project memory entry** — `enemy-ai-state-machine.md` had
flagged the general chaser-driver question as an "OPEN residual," when it was actually
resolved the same week it was flagged (the resolution in `enemy_ai_programs.c` was just
never cross-linked back into that memory). Fixed as part of this banking pass.

**D20's core mechanism is BOUNDED/substantially exhausted**, but the encounter's own
3-section structure is NOT yet exhausted. Every mechanism traced — `contact_walker`,
`FUNC_8004A700`, the sibling contact allocator, `scene_setup_and_load`, and the mover-VM
chase gate — turned out to be shared, whole-game-generic machinery, not bespoke boss
code. Remaining gaps in that core layer (the specific defeat-transition caller, the
white-berry overlay's own file identity, source closure, audio) are well-scoped
last-mile items.

**3-section structure investigated, partially — 2026-08-03.** Operator described three
distinct areas: an opening encounter with a UI health drain, a platforming chase where
Hopper retreats to patrol elsewhere after a hit until Flik nears "a gate," and a
mountain-climbing section. None of this had been checked before being asked about — the
honest answer at the time was no.

**Section 1 (health drain) — confirmed with a real nuance.** `id=22`'s own `+0x6e` field
DOES take real `-2` damage on a hit (movie-relative frame 5914, PC `0x800590e4` — inside
`0x80058af8`, the already-Canon generic enemy hit-tail function used campaign-wide) —
contradicting this row's own earlier "static across sessions" read, which had only
sampled two unrelated snapshots, not a live combat sequence. But 2 frames later it's
RESTORED to its prior value via `0x800b418c` — inside the SAME boss-combat-overlay
merged region as the white-berry aim caller (`0x800b46d4`), and suspiciously close to
the archived note's own Thumper-overlay callers (`0x800b4138`/`0x8009c024`) — raising a
new lead that Hopper and Thumper may share ONE combat overlay blob. This exactly
mirrors Thumper's own already-documented pattern: the raw field takes generic damage,
but the real bookkeeping lives in the overlay, which reverses it to prevent an
accidental kill via the shared regular-enemy pathway. Checked 2 screenshots at the exact
hit moment for a dedicated on-screen Hopper health bar (matching Thumper's own
documented "5 red segments") — found none, but this is not exhaustive. The 4 hits Flik
took in this window were a mix: 3 direct-contact, 1 ranged white-berry.

**Section 2 (patrol after a hit) — confirmed structurally, trigger not isolated.**
Immediately after the hit, `id=22`'s chase gate (flags bit `0x2`) reads false and stays
false continuously for ~8,600 frames (~2.4 real minutes) while he moves through a wide,
changing area — not chasing, not frozen. Confirmed back on by movie-relative frame
15000, but that sample coincides with Flik's own on-screen death (part of this
recording's already-documented "poor gameplay" death cycles), not a clean isolated
re-trigger capture. The literal "gate" condition was not identified.

**Section 3 (mountain climb) — CONFIRMED, operator-annotated.** Operator asked directly
whether it was safe to look into section 3 — no blocker, the fixture and technique were
already proven out — and, after a short blind-sampling attempt, supplied the exact
window from memory: *"starts around 11900, flik makes it to the top at around 14645."*
Sampling Flik's own position across that window found his Y coordinate changes
**monotonically** — no reversals across 8 sample points — for a net change of ~338,000
units over ~2,745 frames (~46 real seconds): a genuine, sustained climb, not ambient
wander noise (which elsewhere in this session oscillates back and forth rather than
accumulating in one direction). Screenshots confirm visually: the start looks like the
same walled-maze terrain seen throughout the level; the midpoint shows unambiguous
stepped rock-ledge platforming with a visible drop to a lower area in the background; the
top shows Hopper visible again at a distance. Checking `id=22`'s own state at the top:
his chase gate is still `false` (consistent with the section-2 finding that it stays off
for the whole surrounding stretch), but his own elevation has independently converged to
within ~8,000 units of Flik's — his own generic wander path also climbs the mountain's
terrain, without ever actively chasing up it.

**Correction surfaced in the same pass**: this row had characterized the bird-nest
cutscene as starting "around movie-relative frame ~16100," from a coarse sampling grid
that happened to land after its true start. Direct sampling found it actually begins
around mf15700, immediately after Flik's own death/respawn (lives 8→7) — Flik's position
is frozen bit-for-bit across mf15700–15850 while the camera shows Hopper first riding the
bird's talons, then held in its beak. The already-`accessLog`-confirmed scene_id write at
mf16166 (see the finale-trigger section above) remains correct — it's a *later* event
within this same broader cutscene, not the cutscene's start.

**All three of the operator's named sections are now structurally confirmed and located**
in `movies/Phase4/Interpreter/D20.movie.json`: section 1 (health drain, mf~1669–5914),
section 2 (post-hit patrol, mf~5920–14500 — the climb sits *inside* this stretch rather
than strictly after it), section 3 (mountain climb, mf11900–14645), leading into the
bird-nest cutscene (mf~15700–16300+) and level-complete (mf~16700). Full detail:
`analysis/phase4_d20_hopper.json`'s `PHASE_STRUCTURE_INVESTIGATED_2026-08-03` and
`MOUNTAIN_CLIMB_CONFIRMED_2026-08-03`.

**"The gate" is literal, and the real hp-drain arc was missed on the first pass —
2026-08-03.** Operator supplied three more precise annotations: *"in the first area, 4702
lowers the UI hopper health which makes him run. Around frame 4888 is when he knocks down
the first wooden gate. Around 11825 is when he knocks down the SECOND wooden barrier in
the second area."* This reframed "the gate" entirely — it isn't a Flik-proximity trigger
as originally assumed, it's Hopper himself physically breaking through authored wooden
barriers as part of his own flee path.

Re-armed `accessLog` on `id=22`'s hp/flags from movie-relative frame 0 this time (the
prior pass had armed it around mf5549, structurally unable to see anything before mf4702).
`id=22`'s hp actually initializes to **30**, not 20, and a rapid burst of ~9 hits lands
between mf4245–4745 (500 frames), each the same already-Canon `-2` generic hit, driving hp
down to a floor around 18–20 — where a SECOND overlay restore call site (`0x800b433c`,
alongside the already-known `0x800b418c`) starts clamping every further hit back up. The
operator's mf4702 annotation lands exactly inside this burst window: **crossing the
hp floor is the trigger for both the flee behavior and the chase-gate deactivation**
already confirmed for mf5920 onward — not an arbitrary timer.

Screenshots at mf4888 and mf11825 both show a visually identical X-shaped wooden log
barrier, with Hopper's own model tangled in it; both are confirmed genuinely destroyed
(checked well after each — the structure is completely gone, e.g. by mf12100 Flik stands
in unambiguous climbing terrain). The second barrier sits immediately before the
already-confirmed mf11900 climb start — it's the literal transition into section 3. Most
consistent reading: these are scripted waypoint events along Hopper's own flee path on the
shared mover-VM, whose ISA already includes path-following opcodes (`seek_path_endpoint`,
`path_next_waypoint`, `park_path`) — a hedged hypothesis, not confirmed via disassembly of
the gate-break instruction itself.

**Still an open, unresolved discrepancy**: despite checking 5 frames total across two
passes (including the operator-named mf4702), no dedicated on-screen Hopper health-bar UI
was found — only Flik's own bar and a hit-impact visual effect. Flagged back honestly
rather than claimed as confirmed. Full detail: `analysis/phase4_d20_hopper.json`'s
`GATES_AND_REAL_HP_DRAIN_CONFIRMED_2026-08-03`.

## D20 (Hopper) — the real on-screen health bar found, and the prior pass's "no HP bar" read corrected — 2026-08-03

The "unresolved discrepancy" above is resolved, and the correction runs deeper than just
finding the bar. The operator posted a screenshot of the actual bar (top-left, 5 red
segments) with: *"It's the 5 bars up here. Something is triggering this to lower down."*
This falsifies both this row's own just-prior "not found" read AND the much older archived
`Systems_Enemy_AI_state_machine.md` claim that Hopper has **no** HP bar at all ("Defeat is
scripted phase/trigger progression, not HP-depletion").

**Found by reading the source, not guessing addresses.** `src_re/hud_800526f4.c`
(already-Canon, already-decompiled `FUNC_800526F4` HUD-draw routine) documents: *"Scenes
2/11/13/14/15 select the raw progress globals above and render a common five-segment
tile-0x75 meter"* — with `G_HUD_SCENE15_PROGRESS = 0x800b4ba8` already named for scene 15
(Hopper's own canyon-showdown scene) right in the same file's macro block.

**A methodology bug caught and fixed along the way**: `movie.startPlayback` defaults
`load_start_state` to **false** — an early poll-only check without that flag silently
replayed the movie's inputs onto boot-state garbage (`scene_id` read 0 or 12, `id=22`
absent) instead of the real fight. Passing `load_start_state:true` fixed it immediately.
Worth re-checking any future fresh-instance D20 work for this same mistake.

**Full write trace** (`accessLog` armed from movie-relative frame 0, advanced to the
finale, 20/20 events captured, no truncation): the counter initializes 0→30 at mf1170
(`0x800b3b04`); the first hit-decrement 30→28 fires at **mf4697** — within 5 frames of the
operator's own named mf4702 — via a distinct first-hit handler (`0x800b4164`); nine more
`-2` decrements (28→…→10) fire via a shared regular-hit handler (`0x800b41c8`) spaced
roughly every 1000–1500 frames across the whole fight (mf5916 through mf14772); eight `-1`
decrements (10→…→2) fire via a *different* handler (`0x800b4270`) in a tight late-fight
cluster (mf14836–mf15438); a final write (`0x800b428c`) snaps 2→0 at **mf15490**,
immediately before the already-confirmed bird-cutscene onset (~mf15700).

**Segment count = `ceil(value/6)`**, visually confirmed at three independent, widely
separated points: value 30/28 → 5/5 lit; value 24 (mf7200) → exactly 4/5; value 2 (mf15450,
bird's wing already visible entering frame) → exactly 1/5.

**This corrects, not merely supplements, the prior pass's "real hp arc" framing.**
`actor+0x6e` (init 30, burst-drained to a floor ~18–20, restored by the overlay) is real
and accurately reported, but it is a **secondary/decoy field** — not what the bar shows,
not what gates defeat. The true, on-screen, unclamped defeat counter is `0x800b4ba8`,
which keeps draining long after `actor+0x6e` has already floored. The mf4702
flee-trigger correlation still holds (both fields react to the same hit-burst), but the
mechanism is now precise rather than inferred.

**This closes, for Hopper specifically, the exact residual the archived note left open for
Thumper**: *"HP field + per-hit delta + N-hits-to-defeat — the bar visibly depletes... but
the counter is in the overlay, not isolated."* It also hands Thumper's own row a ready-made
lead: `hud_800526f4.c` documents the identical mechanism for scene 14
(`G_HUD_SCENE14_REMAINING @ 0x800b4cc8`), and Bug Bar's player-facing stage 9 is already
established to run as scene 14 — strongly suggesting Thumper's own "5 red segments" bar
works the same way at a different address. Not verified live this pass (Thumper/E11 are
other agents' active work this session); noted here, not claimed solved for Thumper.

**An unrelated, pre-existing Canon inconsistency surfaced while checking candidate health
addresses**, not created by this pass and out of scope to resolve here:
`MEM_800A6500_Player_state_800A6500.md` calls `0x800A6594` Flik's own "true health," while
`src_re/player_health.c` (RCG-021) calls the same address the health-leaf mercy-drop
counter and names `0x800A7E2A` (full = 7) as the real displayed health. Flagged for whoever
owns Flik's own health-economy row; `0x800A7E2A` was independently confirmed this pass to
read wildly inconsistent values frame-to-frame during live gameplay, consistent with
`player_health.c`'s own documented caveat that it is HUD-animated and unreliable to poll
mid-motion.

Full detail: `analysis/phase4_d20_hopper.json`'s `REAL_HEALTH_BAR_FOUND_2026-08-03`.

## D20 (Hopper) — defeat-trigger caller and overlay file identity closed, gate-break opcode narrowed — 2026-08-03

Operator: *"go for those three items in well-scoped [way]"* — the three residuals from the
prior report. Two close cleanly; the third makes genuine progress without reaching the
specific answer.

**Defeat-trigger caller — CLOSED.** An execute breakpoint at `scene_setup_and_load`'s own
entry (`0x8005038c`), advanced in small steps to catch the exact register state, hit at
movie-relative frame 16150 with `$ra = 0x800502d8`. `functionBounds` on that address
returns `0x800502c4-0x80050388` (confidence exact) — exactly `fmv_sequence_completion_check`,
already the "strongest candidate" from the earlier finale-trigger pass. Disassembly of the
call site confirms it precisely: `jal 0x8005038c` at `0x800502d0`, with `a0=4` and `a1=128`
set immediately before/after — matching the captured registers exactly. **Confirmed, not
merely inferred.**

**Overlay file identity — CLOSED.** Used the project's existing cold-boot warp lever
(`tools/trace_warp_landing.py`'s technique: poke the scene-select table before the
front-end reads it, replaying `flik_to_level01_stall.mv.movie.json` from boot). The tool's
own docstring says to poke table index 1 ("LEVEL01 = idx1") — that claim did NOT hold for
this specific boot movie targeting scene 15; a sustained poke of index 1 held (confirmed
via direct reads) but still landed on the table's own index-0 value (17). Poking **index 0**
instead correctly landed `scene_id=15, stage=15`. The player object itself never spawned
from this raw divert, but that didn't matter — `transferLog` was armed from the moment of
the poke and captured the level's own CD-ROM loads regardless. `transferLog.resolve` on the
already-known overlay addresses (hp-restore sites, white-berry spawn caller, the new
health-counter writer PCs) resolve unambiguously to **`LEVEL05/LEVEL1.DAT`**, uncompressed,
with an exactly-linear RAM-to-file-offset mapping across every address checked. A few
addresses right at the region's start resolve *ambiguously* — one candidate is an earlier,
unrelated `LEVEL00/LEVEL.RAW` load sharing the same fixed RAM slot, ordinary PS1-style
overlay-address reuse, not a real conflict. Addresses further out resolve instead to a
*different* file, `LEVEL05/LEVEL5C.VB` (an audio bank) — meaning the 121,200-byte "merged,
low-confidence" region `functionBounds` flagged earlier this session was never one coherent
function: it's CODE early, then the same RAM reused later for streamed audio, which is
exactly why the static heuristic scan produced an implausible size. **This refutes the
"Hopper and Thumper share one overlay" hypothesis** floated in an earlier pass — Thumper's
own overlay is the separate `LEVEL04/LEVEL1.BIN`; they merely share a per-level naming
convention (`LEVEL1.{DAT,BIN}`, a "slot 1" overlay) and a similar fixed load address, the
ordinary overlay pattern, not one shared file.

**Gate-break opcode — NOT closed, but narrowed with a real finding.** A separate,
already-closed row (`E07_event_vm`) had already statically mapped the mover-VM's op12
CALL-table: `LEVEL05-1 slot 5 / program 28` → overlay predicate `0x800B3BD4`, with exactly
one active record campaign-wide — matching Hopper's own singular actor instance. Setting an
execute breakpoint there and tracing live: the predicate first fires at movie-relative frame
4700-4701 — within 1-2 frames of the operator's own named mf4702 — with `a0=a1=0x800a0224`
(Hopper's own actor pointer). Disassembly of the immediate caller (inside the mover-VM
interpreter itself) shows a per-actor wait-counter handler: increments actor `+0x5e`
(refining E07's own static description — it called this a "resident halfword," but it's
actually actor-relative, since `0x800a0224+0x5e = 0x800A0282` exactly, for Hopper's specific
instance), compares against a per-program threshold, and sets the branch flag `s3` when the
threshold is crossed. But continuing the trace to mf11900 (spanning both gate events) found
this predicate fires **hundreds more times** throughout the whole patrol phase, every
6-30 frames — not uniquely at either gate. It's a general, recurring check in Hopper's own
ordinary patrol loop, not a rare, gate-specific trigger. **Ruled out as the answer, not
ruled in** — the real gate-break instruction is still unidentified. One anomaly noted, not
chased: the last sampled call before mf11900 showed a *different* actor pointer
(`0x800a0644`), suggesting this predicate may also fire for another actor near the second
gate.

Full detail: `analysis/phase4_d20_hopper.json`'s
`DEFEAT_CALLER_OVERLAY_AND_GATE_OPCODE_2026-08-03`.

## Evidence
[[EXP_2026-07-09_understanding_u3]] (op5/14/24 live) · [[FUNC_8004C13C_FUNC_8004C13C]] (interpreter + ISA) ·
`src_re/enemy_ai_programs.c` (hand decode + behavioural sweep). Related: [[Enemy_spawn_architecture]] ·
[[SYS_enemy_death_and_permanence]] · [[Enemy_relocation_method]].
