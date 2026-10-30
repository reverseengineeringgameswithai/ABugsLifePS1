---
kind: experiment
id: EXP_2026-08-04_phase4_c16_lives_gameover
status: complete
source_state: original_game
system: [SYS_level_results_screen]
row: C16_lives_gameover
---

# Phase 4 C16: the lives lifecycle, the decrement, and game over

## Method note — why the first search was wrong

Grepping r2's function listings for `0x65a0(` found **six** stores to lives `0x800A65A0`, none of
them a decrement, which pointed at "the decrement must be in an overlay" — the same shape C05
found for the results screen. That was wrong. The listings only cover the functions r2 identified.

Scanning the **raw image** for any load/store carrying the immediate `0x65A0` finds **23 accesses,
10 stores**. The tool re-runs that scan as a self-check and hard-fails unless it sees exactly
23 / 10 / 1. Lesson, and it is the mirror of C05's: *a listing grep bounds what r2 parsed, not what
the image contains — scan the image when the question is "is there any other writer".*

No overlay touches lives at all (`BITS/MEMORY.BIN`: zero hits). The whole lifecycle is resident.

## The ten stores

- **Eight grants** — `lives + 1`, every one guarded by `sltiu v1, 9`, so **the lives cap is 9**.
  One of them sits inside the grain-pickup body, i.e. the 50-grain reward path (C02).
- **One save restore** — `0x80055550`, the deserializer.
- **One decrement** — `0x80050210`, the only store preceded by `addiu -1`, inside
  `scene_flow_dispatcher` `0x8004FCA0..0x800502C4`. Exactly where the row's `next` pointed.

## The decrement is the game-over branch

```
v0 = [0x800A65A0]              ; lives
if (v0 == 0) goto 0x800500D4   ; *** GAME OVER ***
v0 = v0 - 1                    ; (delay slot)
[0x800A65A0] = v0              ; otherwise consume one life
```

This gives a **code proof** for the law the registry previously credited to the lifecycle oracle:
lives `0` is playable — it is the final life, and dying on it is what ends the run.

Game over itself: `fmv_bin_load(0x2E, 0)` — **FMV id 46**, the game-over movie — then
`scene_setup_and_load(5, 0x40)`. That puts 46 alongside the other identified FMV ids: 41 is the
true ending and 10 the intro clip (C17/D20).

> **⚠️ Tension, deliberately unresolved.** The registry binding says *"death on lives 0 →
> game-over transition to **scene 0** (lifecycle oracle)"*. The code passes `a0 = 5`. Either `a0`
> isn't a raw scene id, or the oracle observed the settled end state after further transitions.
> I am flagging it rather than quietly picking the convenient reading — this is precisely the
> class of contradiction that produced this session's C05 corrections.

## New-game defaults — `0x80055414`

The census calls it `scene_flow_state_table_init`; it is really the **save buffer initializer**:

| Offset | Value | Meaning |
|---|---|---|
| `buf[0]` | `5` | **initial lives** |
| `buf[1]` | `1` | campaign progress |
| `buf[2..0x14]` | `0` | 19 bytes — exactly the unlock-array span `0x80055478` serializes |
| `buf[0x1C..]` | `0x64,0xFF,0xFF,0xFF,0xFF` ×, to `0x140` | the 64×5 side table |

That independently confirms, from the *initialiser* side, the save schema three separate rows
arrived at — C05's 19-byte span, C17's unlock array, E14's 64×5 table — and supplies C16's own
"initial lives" constant. I did **not** rename the function; "state table init" is defensible and
I have already corrected three census names this session.

## ⚠️ Correction (2026-08-04) — the decrement I named is not the one that runs

The operator recorded `movies/Phase4/Interpreter/C16_lives_gameover.movie.json` (Interpreter, v4,
6706 frames) specifically to settle the open items. It falsified the central claim above within
one replay.

Lives ran **9 → 0** across the run with exactly **9 writes**, and **every one came from PC
`0x8005B34C`** (store `0x8005B348`). `0x80050210` — the site I named "the only decrement" —
**never executed**.

The real death decrement is `addiu a2, a2, -1` at **`0x8005B334`**, stored at `0x8005B348`,
inside **`respawn_transition_state_handler`** `0x8005B134`. That is the right home for it: a life
is consumed on the *respawn transition*, not in the scene-flow dispatcher.

**Why I missed it, and the worse part.** My scan looked back only *two* words for an `addiu -1`;
the real decrement sits *five* instructions before its store. And I encoded that heuristic as a
**passing 23/10/1 self-check** — the exact "never encode an inference as a passing structural
check" failure already in memory from the knockdown-not-a-slot-writer incident. The check has been
changed to assert only the census (23 accesses / 10 stores), with the adjacency count reported as
a heuristic and explicitly labelled as *not* finding the real decrement.

**What `0x80050210` actually is:** a second decrementing store sitting immediately after the
`lives == 0 → game over` test. The **branch** there *did* fire live (`execTrace` on `0x800500D4`:
one hit at emulator frame 20425), so that site is the **game-over check**; its fall-through
decrement is a path this movie never took. Whether it serves a different death class or is
unreachable is now open.

**What still stands:** the 23/10 census, the eight grants capped at 9, the save restore, that no
overlay touches lives, the new-game defaults — and the game-over path itself, now *live-confirmed*:
`fmv_bin_load` fired at the same frame as the game-over entry, and `scene_setup_and_load` at frame
21269.

**Bonus, from reading the real site:** two instructions before the death store, `0x8005B330/40`
reads the power-up word `0x800A6590`, masks `0x20`, and writes it back — so **death clears all
power-ups except bit `0x20`** (super-jump, per B06/B08). Not previously on this row.

**The scene tension is still open.** The `execTrace` register captures came back with no `a0`/`a1`
in the payload, so the arguments weren't read. End-of-movie state is level index `4`, latch `2`,
progress `0x0F` — the settled state after further transitions, which neither confirms nor refutes
"scene 0" or `a0 = 5`.

## Both game-over arguments, captured live

The `execTrace` capture list returned no registers, so I used **halting breakpoints** — with hit
detection on **PC equality**. My first attempt treated `paused` as "breakpoint hit", but
`movie.advanceToFrame` leaves the core paused after *every* frame-step, so it logged five spurious
PCs and burned the loop before reaching the target. Worth remembering: after a frame-step, `paused`
is the normal state, not a signal.

| Call | Frame | Args | `ra` |
|---|---|---|---|
| `fmv_bin_load` | 20425 | `a0 = 0x2E` (46), `a1 = 0` | `0x800500E0` |
| `scene_setup_and_load` | 21269 | `a0 = 5`, `a1 = 0x40`, `a3 = 0x0A` | `0x800500EC` |

Both `ra` values are exactly the instruction after their respective `jal` in the game-over path,
which proves the calls came from there and not from some other caller. **FMV id 46 confirmed
live**, and the static read of `scene_setup_and_load(5, 0x40)` is confirmed verbatim.

### The scene tension was a category error

Operator context: after game over the game plays the **initial attract FMVs and then the title /
press-Start screen**. That is what `scene_setup_and_load(5, 0x40)` leads into.

The registry binding and the code were describing **different things**:

- `a0 = 5` is an *argument* to `scene_setup_and_load` — a target/mode selector. It is never written
  to `0x8008245C`.
- `0x8008245C`, the halfword this project normally calls the scene/level index, holds **4**
  throughout the entire post-game-over window — sampled at movie frames 4604, 5200, 5800, 6400 and
  6704, `0x0004` every time. It retains the **finished level's** index, matching C17's reading of
  that halfword as "the level that just finished".

So neither value is "scene 0". The registry's claim isn't refuted — it simply isn't observable as
`0x8008245C` anywhere in this movie. Either it refers to a different address, or to the settled
title state *after* the attract sequence, which this movie ends before reaching. The claim is now
**precisely bounded rather than vaguely contradicted**.

## The continue path, and "scene 0" confirmed — v2 movie

The operator recorded `C16_lives_gameover_v2.movie.json` as a **new file** (the original is
untouched, so everything already banked against it still reproduces): nine deaths → game over →
attract FMVs → title → **continue** → back into gameplay. 10,029 frames.

**Lives are restored by the save deserializer.** The `0 → 5` write comes from PC `0x80055554` —
the store at `0x80055550` inside `FUNC_80055538` — at emulator frame 18961. So a continue restores
lives by **replaying the save buffer**, not by calling the new-game initializer `0x80055414`
directly. (Whether that initializer seeded the buffer's `5` earlier, this movie can't say.)

Two further writes land at level entry, both at emulator frame 19915: `0x80046C04`, inside
`FUNC_80046B20` — the level-load spawn writer whose second half is C04's enemy-quota constructor —
and `0xBFC02BB4`, which is in the **PS1 BIOS ROM**, i.e. a BIOS routine (plausibly a memcpy or CD
callback) copying a block containing the lives byte. The BIOS one is recorded as observed, not
interpreted.

The run ends in **Training** with 5 lives — Flik at the training chalkboard.

### ⚠️ This corrects my own hedge: "scene 0" is confirmed

The previous pass concluded *"neither value is scene 0"* and that the registry's claim *"is not
observable as `0x8008245C` in this movie."* That hedge was correctly bounded — and it now resolves
**in the registry's favour**. In v2, `0x8008245C` goes `0x0004 → 0x0000` and stays there. The first
movie simply ended mid-attract, before the transition completed.

So **"death on lives 0 → game-over transition to scene 0" is confirmed.** What survives from the
category-error analysis is the narrower and still-correct point: `a0 = 5` is an argument to
`scene_setup_and_load` and is *not* the value written to `0x8008245C` — those two were never the
same quantity, which is why they appeared to conflict.

One nuance kept rather than smoothed over: `0x8008245C` reaches 0 in the same window as the lives
restore — during the **continue / level-entry** phase, not at the game-over instant. The registry
ties scene 0 to the game-over transition; the observation ties it to the continue that follows.

## `0x80050210` is a death class — handing it to D05

C16's last residual turned out to be an **ownership** question. Reading back from the store:

```
v0 = [0x800A6594]        ; TRUE HEALTH (s16, Canon from Phase 2)
bltz v0 -> 0x800501F8    ; health NEGATIVE -> straight to the lives check
v1 = [0x80082504]        ; per-level scene/overlay selector
if (v1 != 6) skip        ; only for the scene whose selector is 6
v0 = [0x800B3FE0]
if (v0 == 0) skip
...                      ; lives-- at 0x80050210
```

`0x800B3FE0` has **exactly one reference in the entire retail image** — this load. No store exists
in the EXE or in `BITS/MEMORY.BIN`, and the address sits in the overlay window *below*
`MEMORY.BIN`'s base, so whatever sets it belongs to a different overlay.

So `0x80050210` is a **distinct, scene-gated death class**: a life consumed through the scene-flow
dispatcher instead of through `respawn_transition_state_handler`, reachable only for one scene and
only when that overlay's global is set. Neither C16 movie took it — consistent, since both were
ordinary damage deaths in a normal level.

That makes it **D05_death_respawn's**, whose `missing` explicitly covers *"all death classes"* and
the death state machine. C16 shouldn't annex it. D05 is another agent's active work right now, so I
did not touch that row, its artifacts, or its registry entry — this section is the hand-off, and
the gate above is everything needed to pick it up.

## Still open

What `0x80050210`'s decrement path is for; the **continue** path itself — the movie ends during
the attract sequence, before the title screen settles, so a continue was never taken; where the
registry's "scene 0" actually lives (not `0x8008245C`, which stays 4); the death-class breadth; and
what gates the eight grant sites — only the 50-grain one is attributed.

## Evidence

`analysis/phase4_c16_lives_gameover.json`; `tools/phase4_c16_lives_gameover.c` (17/17 + the
exhaustive 23/10/1 recount).
