---
kind: system
id: SYS_bird_boss
name: Bird boss/hazard (Birdnest fight + Cliffside hazard)
status: partial
confidence: partial
updated: 2026-08-02
---

# Bird boss/hazard (Birdnest fight + Cliffside hazard)

First live pass on D17_bird this session, now covering both halves of the row's own scope:
the Birdnest boss fight (scene 11) and the Cliffside Canyon ground-hazard reuse of the same
`id=30` actor (scene 6). Full evidence: `analysis/phase4_d17_bird.json`,
`ObsidianVault/Experiments/EXP_2026-08-02_phase4_d17_bird.md`.

## Two distinct manifestations, same level

Both confirmed live in scene 11 (campaign progression table `0x80077FA0`, ordinal 6 ->
chronological "Level 6" -> the already-scoped `F06_birdnest`). No fixture spans both back
to back, so whether they are two phases of one boss sequence or coincidentally share a
scene is a hypothesis, not a confirmed fact.

**The scripted setpiece flyby** — already documented in `src_re/setpiece_spawn_8004d698.c`
(trigger `0x800824dc = -1`, consumed to `-2`; waypoint table `0x80096dc8`; actor
block `0x80090bc0`). Field layout confirmed live: current pos `+0x00/04/08`, a second
waypoint point `+0x0c/10/14`, a lagged pos copy `+0x18/1c/20`, atan2 heading halfword
`+0x26`, state/mode `+0x2c`, type halfword `+0x2e`. In the available fixture this actor
flies a smooth, continuous dive through a canyon corridor at dusk with no player
interaction — Flik's health and position never change during the whole recording.

**The trigger writer, found via a static-only audit pass (`debugger.xrefsTo`, no movie
needed)**: the type-0x3f **kind-0x30 "dewdrop telescope" contact-action handler**, at
`0x80054554`-`0x80054598` inside the already-documented `FUNC_80053814`
(`type_0x3f_construct_contact_action_dispatch`). Flik making contact with a kind-0x30
telescope entry (independently corroborated elsewhere in this project — `green-gem-investigation`
memory: "Green gems = telescope hints, kind 0x30") writes `-1` to `0x800824dc`, saves the
telescope's own loop-ordinal to `0x800823cc` as the waypoint-record index, and zeroes Flik's
velocity + grounded flags to hand control to the camera. Guarded by `bne v0,zero,skip` — only
fires while the trigger is currently idle (`0`), so it's re-triggerable on repeat approaches,
not a hard one-shot. This is a **generic** hint/preview mechanism (any kind-0x30 telescope can
trigger any waypoint record); which specific telescope near Birdnest maps to the bird's own
waypoint record was not traced.

**The combat actor, `id=30`** — a regular chunk-31-spawned actor (not the setpiece), found
in the live actor-pointer table (`0x80090748`) alongside the level's other standard actors.
Max hp **50**, an order of magnitude above the regular D-family enemies solved earlier this
session (which top out around 8) — a genuine boss-scale pool. While uninjured it circles
continuously at a fixed altitude over a wide area (`vm_ip` parked at `0x8007788c`,
`park_seek`, its own dedicated program region — not the shared worm/wall_worm ambush block).

## The combat sequence, cross-verified against operator-recorded movies

Confirmed live, then matched frame-for-frame against operator-supplied timestamps from two
Interpreter-recorded movies (`D17.movie.json`, `D17_Goldberry.movie.json`):

1. **The bird attacks Flik directly** — true health (`0x800A6594`) drops `4→3→2` early in
   the encounter, while `id30` is still undamaged and circling.
2. **Obtaining the gold berry launches the bird higher** — `id30`'s Y jumps from `-60832`
   to `-143376` (more negative = higher, this project's established `+Y=down` convention)
   at the exact frame the operator identified.
3. **A mega homing berry seed plant, not a direct throw, damages it.** The operator: Flik
   must crack open this plant, which fires automatically and repeatedly at the airborne
   bird. `id30`'s hp drops in a steady `-4`/hit staircase (matching the already-established
   generic hit-tail "gold class" damage amount, though the exact projectile-class
   instruction wasn't traced this pass) while its own position stays fixed — consistent
   with an automated turret, not a manual aimed hit.
4. **The bird descends, becoming hittable again**, matching a Y return from `-143376` to
   `-60832` at the operator-identified frame; damage resumes shortly after.
5. **Defeat is a THRESHOLD, not hp reaching 0.** In both movies hp freezes in the `18-22`
   range (never 0), and in the *same frame* `vm_ip` jumps to a completely different part of
   the shared mover-VM bytecode (`0x800776ac`/`0x800776ae`, a `park_arrive_stop`/`jump_back`
   pair — labeled under an unrelated species' program region in `analysis/vm_programs.md`,
   a generic reusable primitive, not evidence of a shared identity) and flags change
   sharply. The operator confirmed this state is genuinely "defeated" — the level-complete
   results screen appearing shortly after is proof of that, not evidence the encounter was
   left unresolved (an earlier draft of this finding got that backwards before correction).
6. **The bird then retreats** (Y climbs further, doesn't descend to the ground) — matching
   the operator's own description, not a fall for a finishing blow. This resolves the
   "retreat" half of the row's own named "retreat/re-engage" gap; whether re-engagement is
   possible was not tested.

## Cliffside Canyon: the same actor as a ground hazard, not a boss

Operator: "Cliffside is not a boss but an enemy that attacks Flik if he lands on the
ground" — then supplied a dedicated fixture, `D17_Cliffside_Bird_Death.movie.json` (527
frames). Confirmed live:

- **`scene_id=6`** at frame 50 — chronological "Level 4" → `F04_cliffside_canyon`. This is
  genuinely the row's own "Cliffside reuse" half, not a guess.
- **`id=30` again, but max hp 101, not 50** — exactly the original D13-mishap data point
  that first (mis)flagged this actor. Confirms the same actor ID really is reused with
  different stats between the two encounters; never damaged in this fixture.
- **The bird's TARGET X/Z position is locked to Flik's X/Z at all times**, at a fixed hover
  altitude — this is `id30`'s AI-setpoint field (`+0x28/2c/30`), not its physical position.
  ⚠️ **Self-caught correction**: an earlier draft of this page (and the artifact) claimed
  "the kill is not reflected in the bird's own actor record at all," reading only this target
  field, which is flat through the kill. That was wrong. The generic actor record carries a
  SECOND, physically-interpolated position field (`+0x04/08/0c`) that a side-by-side check
  (both here and against the Birdnest movies, where the two fields visibly converge at the
  moment of defeat) shows really does move — smoothly chasing the target field every frame.
  Re-reading `+0x04/08/0c` through the kill window shows the bird performing an actual, real
  diving strike: a steady, constant-velocity dive closing from 30037 units above Flik at
  f300 to just 1365 units at **f327** — two frames before the hit. The Birdnest combat-sequence
  claims above used the target field throughout and remain valid as target-setpoint reads (they
  correctly track every behavioral transition); this correction is Cliffside-specific,
  discovered by directly comparing the two fields side by side.
- **Landing triggers it**: `grounded` (`0x800A6582`) flips `0→257` at f192-194, matching the
  operator's "~193-195" almost exactly.
- **The actual hit, pinned to the frame**: the stagger timer (`0x800A6592`, documented in
  `MEM_800A6500` as `-30` on an ordinary contact, `-45` on the death branch) jumps `0→-45` at
  **exactly frame 329** — one frame from the operator's own "falls towards his back at
  around frame 330," and two frames after the dive's closest approach (f327). This is the same
  generic contact-damage handler (`0x8004A814`, inside `FUNC_8004A700` `player_damage_handler`)
  used for ordinary enemy hits elsewhere in the game, routed down its death path — not a
  distinct bird-attack state.
- **The likely caller, narrowed via `FUNC_8004A700`'s own already-Canon 6-caller list**:
  `FUNC_8004ABF4` (`actor_player_contact_resolver`, Canon status `live_confirmed`), which calls
  into the damage handler at its `0x8004B4A0` site and — per its own doc — iterates the live
  actor table at `0x80090748` doing per-actor proximity dispatch against Flik. Live-confirmed
  this pass: `id=30` occupies **slot 0** of that table during the Cliffside encounter, exactly
  the single actor `FUNC_8004ABF4`'s own partially-decoded entry math already reads. Its
  documented radius check doesn't itself evaluate "inside" at any sampled frame though (even at
  the closest dive approach), so the caller is well-evidenced by actor-slot identity and
  call-graph membership but the exact firing branch inside this function's undecoded body is
  still open — a substantial narrowing, not a full closure.
- **A previously-undocumented power-flags bit, exhaustively checked this pass**: `0x800A6590`
  gains bit `0x10` at the same frame (`0x4→0x14`) — not in `MEM_800A6500`'s cataloged bitmap.
  `debugger.xrefsTo` on `0x800A6590` was run against BOTH the Birdnest and Cliffside resident
  RAM images (same 8 static stores both times) and every one individually disassembled — none
  ORs in `0x10`. A parallel grep of the entire hand-disassembled resident ASM corpus found
  nothing either. This is very likely Cliffside-overlay code not yet in the disassembled
  corpus, not a resident writer being missed.
- **Death is a lives decrement + forced reposition, not health reaching 0.** Flik's true
  health stays at `4` through the entire sequence. The stagger timer recovers `-45→0` over
  ~90 frames (1 tick/2 frames), holds at 0 for ~29 more frames while the screen visibly
  fades to black, then at **frame 448** lives (`0x800A65A0`) drops `9→8`, Flik and `id30`
  teleport in lockstep to a new shared location (still X/Z-locked to each other), and
  power-flags/stagger reset.
- **Full timeline**: land (f192-194) → physical dive-in, closest approach at f327 → hit/
  death-branch fires at f329 → stagger recovery (f329-419) → black-screen transition
  (f419-447) → lives loss + reposition (f448).

## ⚠️ A live methodology finding, not specific to this row

This investigation live-caught (via direct operator observation of real 60Hz playback) that
an isolated instance launched through the **generic** fork launcher desyncs movie replay
silently — `movie.status.reproducible` stays `true` throughout even though the actual
recorded gameplay content is lost (an early trace on the mis-launched instance showed
`id30`'s hp flat at 50 for an entire movie that, replayed correctly, shows a full combat
sequence). Root cause: the generic launcher's `settings.ini` has no `[CPU]` section and
doesn't seed the memory card. `tools/launch_repro_playback.sh` exists specifically to fix
this and should be used for ALL movie-replay work on this project, not just instrumented
tracing. Full detail: `analysis/phase4_d17_bird.json`'s
`METHODOLOGY_MOVIE_DESYNC_ROOT_CAUSE_2026-08-02`.

## Still open

Whether the flyby and the `id=30` fight are the same sequence; which specific telescope
ordinal near Birdnest maps to the bird's own waypoint record (the trigger mechanism itself is
closed — see above — this is just the specific mapping); the shooter-plant's own mechanism
(planting/activation/targeting — inferred only from its effect on the bird, never directly
examined); the exact damage-instruction PC; re-engagement; the results screen's unlabeled
`0/4` and `00/09` counters; the exact branch/threshold inside `FUNC_8004ABF4` that fires the
Cliffside contact (the caller function itself is now well-evidenced, the exact branch isn't);
the undocumented power-flags bit `0x10` at the Cliffside death branch (exhaustively checked
against all known resident writers this pass and not found among them); a scripted oracle;
source closure.

## Evidence

`analysis/phase4_d17_bird.json` · `ObsidianVault/Experiments/EXP_2026-08-02_phase4_d17_bird.md` ·
`src_re/setpiece_spawn_8004d698.c` · `analysis/vm_programs.md` ·
`ObsidianVault/Canon/Memory/MEM_800A6500_Player_state_800A6500.md`. Related:
[[Enemy_spawn_architecture]] · [[SYS_enemy_ai]] · [[SYS_enemy_death_and_permanence]].

## Defeat, re-derived 2026-08-04

⚠️ Supersedes the "vm_ip jumps to park_arrive_stop/jump_back" reading — those opcode names are
fiction ([[EXP_2026-08-04_mover_vm_indistinguishable_opcodes]]).

**Defeat parks the bird's mover-VM in a null program.** `0x800776AC` is the interpreter's shared
loop tail (no operation body) and `0x800776AE` jumps back to it: an infinite do-nothing loop. The
bird's AI is **halted**. Its "circling" IP `0x8007788C` is likewise just the yield inside an ordinary
`wait_random` → `random_dir_step` → loop wander program.

**The "HP freezes at 18-22" mystery is a PER-HIT RESTORE**, not a freeze and not a phase change.
`0x800B3F34..0x800B3F98`: if the damage is exactly **3** *and* `[0x800A6597] == 3`, the overlay
restores HP to its reference — so those hits never stick. A **−4** hit fails the first test and
lands. Nine −3 hits were restored; the −4 hits then walked HP 50 → 18, where `0x800B4158` installs
the halt program.

The −3/−4 split comes from `berry_tough_damage_dispatch`'s own branch chain on a **berry-type**
value (`0x800590A4..0x800590D4`: type 127 → −4, type 128 → −3, two arms → −2, default −1).

⚠️ `0x800A6597` is **not** that berry type — it is the 64×5 side-table index used four instructions
later at `0x800590F0`. A hypothesis that the index drove the split was traced and **refuted**: it
holds 3 for both −3 and −4 hits.

The counter at `0x800B441C` gates the **launch-high**, not the restore: `0x800B3E50` reads it, and
while `< 5` the overlay writes `0xFFFDCFF0` into the bird's anchor Y and target Y and clears flag
bit `0x02`. That is "obtaining a gold berry launches the bird higher" — **capped at five launches**
(measured 0 → 5 while nine restores occurred).

The fight ends on a **threshold**, exactly like [[Thumper_boss_fight]] (`HP <= 20`). Same HP-latch
pattern as [[SYS_thud_bug_bar_boss]]. All damage comes from one PC — **`0x800590E4`**
(`berry_tough_damage_dispatch`), the same instruction that damages Thumper.

**The defeat block is a shared boss template** (`LEVEL01/LEVEL1.BIN`, identified by writer PC): goal
latch `[0x800823A0] = 1`, `[0x80082470] = 150`, `jal 0x8004DA94` with cinematic-camera flags `= 2`
([[SYS_cinematic_camera]]), boss flags `andi 0xFFFD / ori 0x80`, then the boss-specific disable.
Thumper instantiates the same template with `+0x62 = 10000` instead of a VM park.

Post-halt motion (the "retreat") is **overlay-driven** — Y written by `0x800B42B8` — since the VM is
doing nothing.

### Damage table, and the Cliffside invulnerability explained

The berry type is a **byte at `projectile + 0x2C`** (fixed resident pool: base `0x800B0D18`,
entries from `+8`, stride `0x38`). `berry_tough_damage_dispatch`:
type 0 → −2, 1 → hp−99, 12 → −2, **127 → −4**, **128 → −3**, default −1.

⚡ The gate at `0x80059068` — `slti v0,v0,100` — means **a target with HP ≥ 100 never reaches the
damage table**. That explains why the same actor id=30 at Cliffside carries **hp 101** and is
recorded as "never damaged": 101 ≥ 100. The Cliffside bird's invulnerability *is* its HP value.

✅ **Confirmed live** by register capture at a breakpoint on **physical** `0x000590E4`
(`hit_count: 19`): type **128 → −3** (nine hits, each restored — the gate requires damage == 3) and
type **127 → −4** (eight hits, walking HP 46 → 18 to the threshold). The switch from 128 to 127 is
exactly where the restores stop. Which *named* berry each type is remains unmeasured.

⚠️ Breakpoint addresses must be **physical** (`addr & 0x1FFFFFFF`); the KSEG0 form is accepted,
reports `enabled: true`, and never fires — the same rule as `transferLog.resolve`.

Evidence: [[EXP_2026-08-04_phase4_d17_bird_defeat]], `analysis/phase4_d17_defeat.json`,
`analysis/phase4_d17_berry_types.json`.
