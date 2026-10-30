---
type: experiment
status: complete
date: 2026-08-02
system: enemy AI / D13 armor + aggro
phase: 4
artifacts:
  - analysis/phase4_d13_shell_bug_armor.json
  - tests/test_phase4_d13_shell_bug_armor.py
---

# Phase 4 D13 (shell_bug) armor mechanic and aggro test

## Question

D13_armored_beetles was unresolved: what defeats the "berry-tough" armor
(`flags+0x5c` bit `0x40`), and does this species actually chase the player? Both
questions were directly operator-prompted mid-investigation rather than guessed at.

## Provenance

- Authority: hash-verified pristine retail `SCUS-94288`; ALLMODS not used.
- Fixture: `shell_bug.sav`, media-verified against the pristine disc
  (`emulator.getStateInfo`) before every load — four separate load cycles this pass, one
  per damage-class-sweep trial plus the aggro test.
- Isolated instance: config `/tmp/duckstation-debugger-d13`, port `23500`, never the
  operator's own; stopped via the launcher after every session.

## Method

**Armor sweep**: for each of the 5 native berry classes (red/blue/homing/gold/mega),
loaded a fresh `shell_bug.sav`, poked the equip index (`0x800A6597`) directly rather than
relying on an in-game pickup, then threw one berry and watched both live shell_bug
records' `hp`/`flags` for 90-120 frames.

Caught and fixed a real reliability problem along the way: a single `emulator.pressButton`
call from a paused/frame-stepped context did not reliably reach the throw dispatch
(`0x80047170`) — confirmed via an execute-breakpoint hit-count check that showed 0 hits
across several attempts. Switched to `debugger.resume` (continuous execution) +
`emulator.pressButton {seconds}` + `debugger.pause`, which fired reliably across all 7
throw attempts in this session. Also caught a detection bug: the 64-slot contact pool
(`0x800B0D18`) is densely populated with legitimate scenery records in this fixture, so
"did a new record appear in the pool" is not a reliable throw-detection signal — reading
the target's own `hp`/`flags` directly is.

**Aggro test**: read the actor's runtime-record backlink byte (`+0x80(actor)` → `+0x11`)
first to confirm the already-pinned CHASE-bit gate condition (`== 0x64`) was satisfiable
for this species, before concluding anything from a negative movement result. Then placed
a shell_bug 500 units from Flik (its own Y, velocity zeroed, Flik never touched — the
method validated during the D09 audit), landed a hit, and watched 300 frames.

## Result

**Identity**: both live shell_bug actors read `id=18` and runtime type-word `0x1712` —
two independent fields, both matching `Enemy_spawn_architecture.md`'s established table.

**Armor**: red (class 2) does zero damage, confirmed clean over 120 frames. Blue (5),
homing (8), gold (11), and mega (45) all damage normally. Gold reaches the
permanent-kill finalization shape (struck record's `id` clears to `0`, not just `hp`),
matching `SYS_enemy_death_and_permanence.md`'s existing temporary/permanent distinction.
The berry-tough bit gates **only** red — a fixed per-class exclusion, not a graduated
power threshold or a time-based window. The exact gate was unresolved during this D13
pass. Phase 4 D04 later pinned it: `0x80058EE4` tests enemy `+0x5C & 0x40`;
the branches at `0x80058EF8` and `0x80058F08` divert the excluded connecting form
to reaction-only handling, and `0x80059054` skips the common damage/death path. See
`EXP_2026-08-03_phase4_d04_berry_immunity_matrix`.

**Aggro**: the CHASE bit sets on a hit (flags `0xc041→0xc043`), via the same global
setter (`0x8005914C`) pinned during the D09 audit. But it produces **zero** movement
response — the actor walks its own path for ~90 frames (ordinary movement, not directed),
then stops completely and stays at an exact fixed position for the remaining 210 frames
with the bit still set. This directly confirms the operator and corrects an archived note
(`Enemy_AI_movement_programs.md`) that grouped "shell_bug/canyon_bug" under "wander +
chase" by shared bytecode address — canyon_bug was independently, behaviorally confirmed
chasing in that same original sweep; shell_bug never was, and now isn't.

## Reproduction

```bash
python3 -m pytest -q tests/test_phase4_d13_shell_bug_armor.py
```

The live portions (the 5-class damage sweep and the aggro test) are not yet scripted into
a single runnable tool — both were unrecorded manual play this pass, matching the D09
row's own item-1 gap.

## Follow-up 2026-08-02: id=11 identified (operator: "identify the id=11 actors")

Three `id=11` actors were present in the same fixture. Read each one's runtime-record
type-word (via the `+0x80` backlink): `0x000B`/`0x030B`/`0x040B` — low byte `0x0B` (11)
confirms the id; high bytes `0x00`/`0x03`/`0x04` differ. Their `vm_ip` values
(`0x8007745C`/`0x800774FC`/`0x8007755C`) turned out to be an exact match, entry for entry,
against the 13-slot program table `0x80077AF8` read directly — indexed exactly by each
actor's own type-word high byte. This resolves a **whole-project residual** the archived
`Enemy_AI_movement_programs.md` note named explicitly ("GAP-0033: which record field
selects the program") — the answer is the type-word high byte, cross-checked against
Redbug (high byte `0x0C`=12 → table entry 12 → Redbug's own program) for a second
confirmation.

Visually identified via `emulator.captureFrame`: moved an `id=11` actor to within 800
units of Flik (own Y, velocity zeroed, Flik untouched) and captured it in-frame, repeated
with a second `id=11` program-variant for comparison, then captured an `id=11` and
shell_bug together in one frame. Result: `id=11` is a large beetle with a yellow,
black-spotted shell, a black/white speckled underside, a green thorax, and blue-purple
legs — visually large and ornate, clearly distinct from shell_bug's small plain tan oval
shell (confirmed side by side). The two program-variant instances look identical to each
other — the high byte changes movement assignment only, not appearance. Screenshots were
not committed (copyrighted game media); described here instead.

No internal or external name is established for `id=11` in anything checked —
`analysis/phase1_kind_actor_census.json` lists it `unknown_role`; `config/record_types.yaml`'s
own guess ("movable seed") is directly contradicted by this pass's live evidence (a
moving, HP-bearing, mover-VM-driven shelled actor is not a movable seed object) and
should be treated as superseded, not authoritative. Given the row's own name and that this
creature visually fits "armor-plated beetle" far more than shell_bug does, it is plausibly
the row's primary family member — a reasonable inference, not proven.

## Follow-up 2026-08-02: scope confirmed with the operator, id=11 speculation superseded

A live session (isolated instance, `canyon_bug.sav`/`canyon_bug_aggro.sav`) attempted to
resolve the shell_bug/canyon_bug shared-bytecode aggro puzzle above. The operator caught a
real mistake mid-session: the actor being repositioned (`id=30`, HP `101`, `vm_ip`
`0x8007788C`) was *"the bird you're lowering"* — an ordinary `LEVEL04` enemy, not
canyon_bug at all. The operator identified the actual canyon_bug as `id=37` (HP `2`, two
instances, `vm_ip` in spider's own program region) present in the same fixture, and then
clarified this row's real scope directly: *"the row is for that shell bug in LEVEL04
(which is LEVEL07 in chronological order)?"* — confirmed yes, cross-checked independently
against the campaign progression table (`0x80077FA0`): ordinal 7 → scene 4 → disc
`LEVEL04`, an exact match.

A static scan (same method as the shell_bug campaign-breadth check) found canyon_bug
(`id=37`) spawns in `LEVEL01`/`06`/`08`/`10` — **never** `LEVEL04` — so it does not share a
level with shell_bug despite the archived note's shared-bytecode grouping. A second static
check found `id=11` has **130 records across 16 of ~21 campaign RAW files** — a common,
campaign-wide actor, not a rare special encounter. This **supersedes** the earlier
speculation that `id=11` might be D13's primary family member (that reasoning assumed a
rarity/specialness matching shell_bug's own single-level exclusivity, which does not
hold). Both `id=11` and canyon_bug are confirmed real, distinct, unrelated species — **out
of scope for this row**, not pursued further here.

One genuine, if unconfirmed, piece of progress survived the detour: cross-referencing
shell_bug's own `vm_ip` (`0x80077826`, `park_path`) against the address the archived note
associates with canyon_bug's section of the shared program (`0x8007788C`, `park_seek` —
the same chase-compatible primitive Redbug uses) gives a plausible mechanical explanation
for why one chases and the other doesn't. Not live-confirmed against a verified canyon_bug
instance, since the same-day live session tested the wrong actor.

## Follow-up 2026-08-02: in-session respawn tested, negative (parallel to D09)

Direct parallel to the D09/Redbug respawn test. Sixth isolated instance this row, port
`23504`, config `/tmp/duckstation-debugger-d13-respawn`, stopped via the launcher at the
end. Fresh `shell_bug.sav` load, media-verified. Equipped blue, landed two hits (HP
`3→1→0`, matching the already-established `-2`/hit shape; `id` retained, confirming the
temporary-KO shape rather than gold's permanent-clear shape), then watched continuously
in 200-frame steps out to 4000 total frames (~66s at 60Hz).

`hp` stayed exactly `0` at every sample. No revival observed. Same negative result as
D09's Redbug — a second species now confirming the actor-record architecture (records
rebuilt only on level load, not reallocated during play, and this specifically holds for
the temporary-KO case).

### ⚠️ RETRACTED, later same day

The negative result above was banked from a test where Flik never moved after the kill.
The operator corrected this with direct gameplay knowledge — enemies come back, but only
after the player actually leaves and returns, not while standing nearby. Live re-tests
with Flik genuinely walking away confirmed a full reset for Redbug (D09) and worm (D12) the
same day; shell_bug was not independently re-run live, but the test design here is
identical, so the retraction applies on the same basis rather than being left standing on a
technicality. The mechanism was ASM-traced under D12 to a previously-undocumented
reinstantiate-from-spawn-template routine (`0x80049C2C`), with two named open questions
(its exact trigger, and a contradiction in a nearby distance-admission check) — full detail
in `analysis/phase4_d12_worm_id40.json`'s `RESPAWN_MECHANISM_2026-08-02` and
`SYS_enemy_death_and_permanence.md`.

## Residuals

Scoped to shell_bug specifically (canyon_bug and `id=11` are confirmed out of scope):
scene-reload respawn (not tested,
near-tautological given the loader architecture); pause/scene-transition lifecycle; a
scripted/recorded oracle; cross-system audio, interfaces, and source closure; an
independent live re-confirmation of the walk-away respawn specifically for shell_bug.
