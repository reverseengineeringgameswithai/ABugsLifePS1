---
type: experiment
status: complete
date: 2026-08-02
system: enemy AI / D17 bird boss (Birdnest)
phase: 4
artifacts:
  - analysis/phase4_d17_bird.json
  - ObsidianVault/Canon/Systems/SYS_bird_boss.md
---

# Phase 4 D17 bird boss/hazard — Birdnest combat sequence + Cliffside hazard

## Question

D17_bird was unresolved: "Attack, retreat/re-engage, shooter interaction, Cliffside
kill-zone reuse" all named missing. Picked as the next row after D12 was closed out,
partly because an earlier session (D13) had accidentally stumbled onto the actor (`id=30`)
while misidentifying it as canyon_bug, giving a small head start. This note now covers both
halves of the row's scope: the Birdnest boss fight and the Cliffside ground-hazard reuse.

## Provenance

- Authority: hash-verified pristine retail `SCUS-94288`; ALLMODS not used.
- Fixtures: `bird.movie.json`/`.sav` (repo root, scripted setpiece flyby), and two
  operator-recorded, Interpreter-format movies under `movies/Phase4/Interpreter/`:
  `D17.movie.json` (2759 frames, "beating the level") and `D17_Goldberry.movie.json`
  (5674 frames, "the gold berry"). A third file, `D17.json` (2639 frames), was also
  present but turned out to be a walk that never reaches the bird's trigger point.
- Isolated instances: multiple across this investigation (see the methodology section
  below for why); the final, correct one launched via `tools/launch_repro_playback.sh`,
  config `/tmp/dsrepro-d17`, port 23514, never the operator's own.

## A significant methodology detour: movie desync

Early in this investigation, live-timing experiments to trace the scripted setpiece's
spawn trigger (`0x800824dc`) kept returning zero `accessLog` hits despite the bird
demonstrably spawning — initially attributed to the already-known gap between
`movie.advanceToFrame` (proven safe) and real `debugger.resume`-driven 60Hz playback (not
yet proven). Recording a fresh Interpreter movie and re-testing confirmed *that* hypothesis
partially — `accessLog` reliably caught a real write event this time — but the actual
`-1` trigger write was still never caught, only a `0`-write from the level's own generic
reset routine (`FUNC_8005B714`, already Canon).

When the operator asked to watch `D17_Goldberry.movie.json` play back at real speed to
judge desync themselves, they immediately identified visible desync on the FIRST properly-
launched instance too — even after correctly predicting the CPU-mode-forcing risk. A
controlled RAM-hash comparison (pure `advanceToFrame` replay vs. a replay that switched to
real `debugger.resume` partway through) showed measurable divergence (Flik position off by
~1500 units, differing SHA-256 of the full 2MB RAM image at the same nominal frame),
consistent with — but not a clean isolation of — the CPU-mode-forcing hypothesis.

The operator pushed to "brute force a fix... until the end result is the end-level
transition thing." That search found the real root cause: `tools/launch_repro_playback.sh`
already exists specifically to solve this, and its own header comments explain why —
**the generic fork launcher (`launch_debugger_instance.sh`) writes a `settings.ini` with no
`[CPU]` section and doesn't seed the memory card the movies were recorded against.** This
had been used for the entire investigation up to that point. Relaunching via the repro
script (`--execution-mode Interpreter`) and replaying the same movie: operator confirmed
"syncs properly now."

**The consequence was not cosmetic.** A trace of `id=30`'s hp across the whole
`D17_Goldberry.movie.json` on the mis-launched instance showed hp flat at 50 for all 5674
frames — apparently no combat at all. The identical trace, re-run on the corrected
instance, showed a full combat sequence (two hits landing on Flik, nine hits landing on the
bird, hp `50→18`, a clean state transition). `movie.status.reproducible` reported `true`
throughout on BOTH the broken and the corrected instance — this failure mode has no error
signal at all. Banked as a new gotcha (`duckstation-trace-gotchas` memory, gotcha 4):
**use `tools/launch_repro_playback.sh` for ALL movie-replay work, not just instrumented
tracing.**

## Method (after the fix)

Live actor-record reads via `movie.advanceToFrame` sampling of `id=30`'s own fields (`+0x00`
id, `+0x6E` hp, `+0x5C` flags, `+0x28/2C/30` pos, `+0x70` vm_ip, matching the established
generic actor-record schema) and Flik's true health (`0x800A6594`), cross-checked against
`scene_id` (`0x80082504`, read a few frames in to avoid a boot-transition stale value) and
against operator-supplied precise frame timestamps from their own recording session.

## Result

**Level identity**: all three available fixtures read `scene_id=11`. Per the
campaign-progression table already established this session
(`[17,1,3,2,6,10,11,4,5,14,7,12,13,9,8,15,-1]`), scene 11 is ordinal 6 → chronological
"Level 6" → the already-scoped `F06_birdnest`. Both the scripted flyby and the `id=30`
combat encounter are in this same scene — a real surprise, since the flyby's visual
dusk-canyon backdrop had suggested `F04_cliffside_canyon`. Most likely explanation: the
flyby and the fight are two phases of one boss sequence, but this is a hypothesis — no
fixture spans both.

**Two distinct bird manifestations, confirmed live**:
- The scripted setpiece (`0x80090bc0`), spawn mechanism already documented in
  `src_re/setpiece_spawn_8004d698.c` and confirmed live field-for-field. In the available
  fixture it just flies a scripted dive with zero player interaction.
- `id=30`, a regular chunk-31-spawned actor, max hp 50 (boss-scale — 6x the largest
  regular D-family enemy solved this session), found via the standard live actor-pointer
  table (`0x80090748`).

**The full combat sequence, cross-verified almost frame-exactly against operator
annotations**:

| Event | Operator's frame | Live-verified |
|---|---|---|
| First hit lands (D17.movie.json) | ~1900 | hp 50 at f1900, 48 at f1910 |
| Bird defeated (D17.movie.json) | ~2320-2330 | hp freezes at 20, state transition, exactly f2330 |
| Retreat cutscene (D17.movie.json) | ~2360 | Y still climbing at f2360, matches "retreating" |
| Gold berry obtained (D17_Goldberry) | ~2710-2715 | Y jumps -60832→-143376 exactly at f2715 |
| Homing attacks (D17_Goldberry) | ~3822-4650 | hp still 50 through this window; likely covers activation + descent, not connecting hits |
| Bird descends (D17_Goldberry) | after ~4650 | Y returns -143376→-60832 at f4650-4700 |
| Final hit (D17_Goldberry) | ~5055 | hp 22 at f5055, freezes at 18 at f5060 |

**The central mechanical finding**: defeat is a **threshold**, not hp reaching 0. Both
movies show hp freezing in the 18-22 range, in the exact same frame as `vm_ip` jumping to a
completely different part of the shared mover-VM bytecode (`0x800776ac`/`0x800776ae`, a
`park_arrive_stop`/`jump_back` pair — labeled under an unrelated species' program region in
`analysis/vm_programs.md`, confirmed to be a generic reusable primitive there, not evidence
of a shared identity) and flags changing sharply. **The operator directly corrected an
earlier draft of this finding**, which had misread the frozen hp and the bird's continued
climb (not descent) after this point as "the fight was left unresolved" — the level-complete
results screen appearing shortly after in `D17_Goldberry.movie.json` (grain 24/50, an
unlabeled 0/4 counter, an unlabeled 00/09 counter) IS the proof of defeat, not evidence
against it.

## Cliffside Canyon: same actor, ground hazard not a boss

Operator, after the Birdnest work: "Cliffside is not a boss but an enemy that attacks Flik
if he lands on the ground" — then recorded a dedicated fixture,
`movies/Phase4/Interpreter/D17_Cliffside_Bird_Death.movie.json` (527 frames, format v4),
placed directly in the same `movies/Phase4/Interpreter/` directory without being asked.

**Level identity**: `scene_id=6` at frame 50 → chronological "Level 4" → the already-scoped
`F04_cliffside_canyon`. This is genuinely the row's own "Cliffside reuse" half.

**Same actor ID, different stats**: `id=30` present again (same live actor-pointer table,
`0x80090748`), but max hp **101**, not 50 — exactly the number the original D13 mishap had
recorded before this session correctly re-identified that actor. Never damaged in this
fixture; it's a pure hazard here.

**The bird hovers at its TARGET position, and dives at its PHYSICAL position** — a finding
corrected during the audit pass below. `id30`'s target position (`+0x28/2c/30`) matches Flik's
X/Z exactly at every sampled frame, only Y differing by a large fixed hover offset; its
`flags`/`vm_ip` (`0x4985` / `0x8007788c`) never change across the whole fixture. An earlier
draft of this note read only that field and concluded "the kill leaves no trace in the bird's
own actor record" — wrong. See "Audit pass" below for the corrected finding: the physical
position field (`+0x04/08/0c`) shows a real diving strike.

**Landing triggers it, pinned frame-for-frame against operator annotations**:

| Event | Operator's frame | Live-verified |
|---|---|---|
| Flik lands (`grounded` 0→257, air state 2→0) | "~193 to 195" | f192-194 |
| Hit / death-branch fires (stagger `0x800A6592` 0→-45) | "falls towards his back at ~330" | **f329** |
| Lives loss + reposition (respawn commit) | (not annotated) | f448 |

The stagger timer (documented in `MEM_800A6500`: `-30` on an ordinary contact, `-45` on the
death branch) confirms the Cliffside kill routes through the **same generic contact-damage
handler** (`0x8004A814`, inside `FUNC_8004A700` `player_damage_handler`) used for ordinary
enemy hits elsewhere in the game — not a distinct bird-attack state.

A previously undocumented power-flags bit surfaced at the same frame: `0x800A6590` gains bit
`0x10` (`0x4→0x14`) at f329, not present in `MEM_800A6500`'s cataloged bitmap
(`0x01/02/04/08/20/80`). See "Audit pass" below for the exhaustive (negative) search for its
writer.

## Audit pass (same day, static analysis only — no new movie captures)

The operator asked for another deep dive before closing this row out. Rather than more
live-movie tracing, this pass used `debugger.xrefsTo` (a live RAM scan for every static
reference to an address) plus targeted disassembly — cheap, exhaustive, and independent of
catching the right frame in a fixture.

**The setpiece spawn-trigger writer, closed.** Paused on the Birdnest save state and ran
`xrefsTo` on `0x800824dc`: 24 static references, 10 stores. Disassembling each and
cross-checking the kind-dispatch jump table (`0x8001b42c`) pinned the writer exactly: the
type-0x3f **kind-0x30 "dewdrop telescope" contact-action handler**, `0x80054554`-`0x80054598`,
inside the already-documented `FUNC_80053814`. It writes `-1` to the trigger (guarded — only
while currently idle), the telescope's own loop-ordinal to `0x800823cc` as the waypoint
record index, and zeroes Flik's velocity/grounded flags. The underlying decompilation already
existed (the source file's own header comment describes this in isolation, and it's
independently corroborated by the project's `green-gem-investigation` memory: "Green gems =
telescope hints, kind 0x30") — what was missing was the explicit cross-reference resolving
`setpiece_spawn_8004d698.c`'s own open "writer is the script/event layer" note. Residual:
which specific telescope near Birdnest maps to the bird's own waypoint record wasn't traced
(this is a generic mechanism reused for many hint/preview flybies across the game).

**A self-caught correction to this same note.** Comparing `id30`'s two candidate position
fields side by side (`+0x28/2c/30` vs `+0x04/08/0c`) on both the Cliffside fixture and the
Birdnest movies showed they are genuinely different: `+0x28/2c/30` is an AI TARGET/setpoint
(jumps discretely at behavioral transitions — confirmed against the Birdnest gold-berry Y
jump, which uses this same field) while `+0x04/08/0c` is the PHYSICALLY-INTERPOLATED current
position (smoothly chases the target; the two fields converge exactly at the Birdnest defeat
freeze, f5060, both reading `-67150`). Re-reading the Cliffside kill window through
`+0x04/08/0c` (not `+0x28/2c/30`, which was flat) shows `id30` performing a real, physical
diving strike: a steady constant-velocity dive from 30037 units above Flik at f300, closing to
1365 units at **f327** — two frames before the f329 hit. The earlier claim in this note ("the
kill leaves no trace in the bird's own actor record") was simply reading the wrong field.
The Birdnest combat-sequence table above used the target field throughout and remains valid —
it correctly tracked every behavioral transition — but should be read as target-setpoint data,
not literal frame-by-frame physical trajectory.

**The Cliffside contact caller, substantially narrowed.** `FUNC_8004A700`'s own Canon page
already statically enumerates its 6 callers; `0x8004B4A0` ("actor_player_contact_resolver") is
inside `FUNC_8004ABF4`, whose own Canon doc says it iterates the live actor table at
`0x80090748` doing per-actor proximity dispatch against Flik. Live-confirmed: `id=30` occupies
**slot 0** of that table during the Cliffside encounter — exactly the single actor
`FUNC_8004ABF4`'s own partially-decoded entry math already reads. Its documented radius check
(`dx²+dy²+dz² < r²`, `r` = actor radius + 250, with a `-7360` Y-bias) does not itself evaluate
"inside" at any sampled frame, including the dive's closest approach — so the caller is
well-evidenced by actor-slot identity and call-graph membership, but the exact firing branch
inside this function's undecoded 2792-byte body is still open.

**The undocumented power-flags bit `0x10`, exhaustively checked, still open.** `xrefsTo` on
`0x800A6590` was run against BOTH the Birdnest and Cliffside resident RAM images — identical 8
static store sites both times (`0x8001d5f8`, `0x8004a7b0`, `0x8004a8e0`, `0x80051eb0`,
`0x80054e90`, `0x8005b340`, `0x8005d088`, `0x800b3d3c`). Every one individually disassembled;
none ORs in `0x10` (found: `0x0001`, `0x0002`×2, `0x0080`, `0x0020` via `andi`, `0x0004`×2). A
parallel grep of the entire hand-disassembled resident ASM corpus
(`asm/nonmatchings/resident/*.s`, 23 files referencing `0x6590`) for an `ori`/`andi` immediate
of `0x10` near a `0x6590` store also found nothing. This is very likely Cliffside-overlay code
not yet in the disassembled corpus — a real, well-characterized negative result, not a gap in
the search.

**Death is a lives decrement, not health reaching 0**: Flik's true health
(`0x800A6594`) stays at `4` through the entire sequence — never drops. The stagger timer
recovers `-45→0` over ~90 frames (1 tick/2 frames, matching the tick rate documented
elsewhere for the invincibility timer), holds at 0 for ~29 more frames while the screen
visibly fades to black (screenshots: mostly visible at f440, fully black f447-449), then at
frame 448 lives (`0x800A65A0`) drops `9→8` and Flik + `id30` teleport in lockstep to a new
shared location (still X/Z-locked to each other post-jump), with power-flags and stagger
reset. This is a direct, precise confirmation of the operator's own framing: "an enemy that
attacks Flik if he lands on the ground."

## Reproduction

```bash
python3 -m pytest -q tests/test_phase4_d17_bird.py
tools/launch_repro_playback.sh --config-dir /tmp/dsrepro-d17 --port 23514 \
  --token debugger-1000 --execution-mode Interpreter \
  --disc "Disney-Pixar A Bug's Life (v1.0).cue"
```

All live reads this pass were unrecorded manual/scripted play driven by
`movie.advanceToFrame`, not a scripted/asserted oracle. The audit pass added
`debugger.xrefsTo` + disassembly as a static-only method, independent of movie fixtures.

## Residuals

Whether the flyby and the `id=30` fight are truly one sequence; which specific telescope
ordinal near Birdnest maps to the bird's own waypoint record (the trigger mechanism itself is
closed, see "Audit pass" — this is only the specific mapping); the mega-homing-berry shooter
plant's own mechanism (planting, activation, auto-targeting — inferred only from its effect
on the bird, never directly examined); the exact damage-instruction PC (behaviorally
`-4`/hit, not traced); whether re-engagement is possible; the results screen's unlabeled
`0/4` and `00/09` counters; the exact branch/threshold inside `FUNC_8004ABF4` that fires the
Cliffside contact (caller function well-evidenced, exact branch not); the undocumented
power-flags bit `0x10` at the Cliffside death branch (exhaustively checked against all known
resident writers, not found among them); a scripted/recorded oracle; cross-system audio/HUD;
source closure.
