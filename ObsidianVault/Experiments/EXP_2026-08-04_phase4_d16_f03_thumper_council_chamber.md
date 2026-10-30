---
kind: experiment
id: EXP_2026-08-04_phase4_d16_f03_thumper_council_chamber
status: complete
source_state: original_game
system: [SYS_cinematic_camera, Thumper_boss_fight, SYS_camera]
row: [D16_thumper, F03_council_chamber]
---

# Phase 4 D16 / F03: 0x80090BEE is a camera field, not a defeat flag

Both rows carried the same binding — *"Thumper defeat at HP ≤ 20 → `0x80090BEE = 2`"* — and the
same `next`: **"trace `0x80090BEE = 2` consumers into the level-exit transition."**

There are no such consumers. The premise is a category error, and unwinding it is what closes
both rows.

## What 0x80090BEE actually is

It is the **flags halfword at +0x2E of the shared cinematic-camera block `0x80090BC0`** — the same
setpiece block [[SYS_camera]]'s neighbours already reach through for the telescope ([[EXP_2026-08-03_phase4_c14_telescope]]) and the bird flyby (D17). Two facts make the old reading collapse:

1. **Only two functions ever write it, and both take the value as a caller-supplied argument.**
   `cinematic_camera_start` `0x8004D9E8` (flags = arg7, stored at `0x8004DA7C`) and
   `cinematic_camera_start_polar` `0x8004DA94` (flags = arg8, stored at `0x8004DB44`). Both also
   set the camera **phase** `0x80090BEC := 2`, which is what actually starts the sequence.
2. **"2" is just the flags value callers pass.** The *resident* telescope setpiece path passes it
   unconditionally (`0x8004D6F4: addiu v1,zero,2`), and so do several level overlays. It is not a
   Thumper-specific code and it is not a defeat state.

### The selector — `0x8004EA8C`

The census name for this function is `enemy_ai_dispatcher`. That is wrong; it is the camera-source
selector. It switches on the phase `0x80090BEC`:

| phase | action |
|---|---|
| 2 | `four_byte_store(0,0,0,16)`; phase := 1; **if flags & 2 → `0x800A6590` \|= 0x04** |
| 1 | wait for `[0x80082388] == 0`; `four_byte_store(128,128,128,16)`; **flags \|= 0x01**; phase := 0 |
| 3 | wait for `[0x80082388] == 0`; `four_byte_store(128,128,128,16)`; phase := 0; **flags &= ~0x01**; if flags & 2 → `0x800A6590` &= ~0x04 |
| 4 | `four_byte_store(0,0,0,16)`; phase := 3 |

Its tail is the payoff: if `flags & 1`, the camera parameters come from the setpiece block
(`setpiece_actor_update(0x80090BC0)`, reached as `addiu a0,s0,-46`); otherwise from the ordinary
follow camera `0x80095358`. Either way the result lands at `0x8009EC50`.

So **bit 0x01 = "cinematic camera active"** and **bit 0x02 = "also hold power-word bit 0x04 for the
duration"**.

## Two claims from the previous session that did not survive

The prior pass read these sites out of a disassembler dump and recorded them unverified. Both of
its interesting conclusions were wrong, and both were wrong in the *plausible* direction.

**"Bit 0x01 suppresses the HUD — probably the boss arena swapping in a Thumper health bar."**
The mechanism is real: `gameplay_state_machine` reads the flags at `0x8004F3D0` and `0x8004F6DC`
and, when bit 0 is set, skips `jal 0x800526F4` (`hud_draw`, per [[EXP_2026-08-04_phase4_e13_hud_results]])
and calls `jal 0x80053638` instead. But `0x80053638` is `draw_mirrored_fullscreen_quads` — this is
**cinematic letterboxing**, not a boss health bar. Nothing boss-specific is involved.

**"Bit 0x02 grants a previously unidentified power-up (`0x800A6590` bit 0x04)."**
The OR is real. The interpretation is backwards. All five readers of bit 0x04 —
`0x8004EED0`, `0x80050C84`, `0x80051138`, `0x80054F38`, `0x80056550` — have the identical shape:
**set → branch past the body**. It never enables anything. Three sit in SFX functions; the one in
`gameplay_state_machine` masks the player action word `0x80082488` down to `0x309`. It is a
**cutscene suppression gate**, which is exactly what a cinematic camera would want, and it is not
a member of the power set documented in [[EXP_2026-08-01_phase4_b06_b08_power_slot]] (0x02 invincibility / 0x08 bubble /
0x20 super-jump — see also [[SYS_player_power_slot]]).

## The census, and why the previous count was wrong

`tools/phase4_d16_f03_static.c` runs **two independent scans** — an immediate-match scan and a
constant-propagation dataflow scan with `$gp` pinned — over the pristine EXE **and all 21 overlay
blobs**, and compares them **as sets, never as counts**. The counts legitimately differ because each
method sees an addressing form the other cannot, so asserting count equality would be an inference
dressed up as a structural check.

Result: **11 accesses — 10 resident and one in an overlay** (`LEVEL02/LEVEL1.BIN` `0x800B4560`,
which tests bit 0x01). The earlier "9 accesses, all resident, no overlay touches it" was wrong on
both counts, and it was also wrong about the **access width**: every one of them is `lhu`/`sh`, not
`lbu`/`sb`.

Two immediate-scan candidates in `LEVEL07/LEVEL1.BIN` are **false positives**: their base resolves
to `0x800B0BEE`, which collides with `0x80090BEE` in the low half. A count-only census would have
reported 13 and been quietly wrong — the reason the tool re-resolves every candidate instead of
counting matches.

## The rows' actual question: where the level exit really is

⚠️ **Region A (`0x800B39A0`) is a shared swap buffer.** Every `LEVEL*/LEVEL*.BIN` loads at the same
VA, so an overlay address means nothing without knowing which blob is resident. The first draft of
this analysis read the Council Chamber defeat code out of **`LEVEL03/LEVEL1.BIN`** — the blob whose
*name* matches the row's scene binding — and was wrong. Hashing the resident region-A window during
the live replay shows the blob actually loaded is **`LEVEL02/LEVEL.BIN`**. Every overlay claim below
is against that blob, and the oracle asserts the identity rather than assuming it.

```
LEVEL02/LEVEL.BIN
  0x800B4070  lh v0,[0x8009FE72]     ; Thumper HP = chunk-31 actor 0x8009FE04 + 0x6E
  0x800B4078  slti v0,v0,21          ; defeat threshold: HP <= 20
  0x800B4090  bne [0x800823A0],0     ; once-only guard: skip if already latched
  ...
  0x800B4118  v0 = 2                 ; the cinematic-camera FLAGS argument
  0x800B4138  jal 0x8004DA94         ; start the cinematic camera
  ...
  0x800B4190  sh v0,[0x800823A0]     ; *** THE LEVEL EXIT *** (v0 = 1)
```

The camera start and the level exit are **two different stores in one straight-line block**, camera
first. `0x80090BEE` is a presentational consequence of the defeat sitting next to the exit, not a
step on the way to it — its complete consumer set contains no read or write of `0x800823A0`, the
scene id `0x80082504`, or any loader entry point.

Note the goal latch doubles as the **idempotence guard**: the block re-runs every frame while HP is
low, and `bne [0x800823A0],0` is what makes the defeat fire once.

This also confirms the registry's pre-existing HP binding exactly: the Thumper actor record is at
`0x8009FE04` and HP is `+0x6E`.

## Live verification

`tools/phase4_d16_f03_oracle.py` → `analysis/phase4_d16_f03_oracle.json`, replaying
`thumper_boss.movie.json` at 60 Hz.

**Poll-only, deliberately.** That fixture predates the Interpreter finding, so arming any
`accessLog` watch / `execTrace` / breakpoint would force `CPUExecutionMode::Interpreter` and desync
it *silently*. The oracle uses `readMemory` only, and records that limitation in its own artifact.

```
i=7     hp=50  goal=0  phase=0  flags=0  power=0   scene=2
i=439   hp=48  ...                                            (-2 per berry hit)
i=1463  hp=22  goal=0  phase=0  flags=0  power=0   scene=2
i=1487  hp=20  goal=0  phase=0  flags=0  power=0   scene=2
i=1495  hp=20  goal=1  phase=1  flags=2  power=4   scene=2    <- defeat fires
i=1511  hp=20  goal=1  phase=0  flags=3  power=5   scene=2    <- bit 0x01 set: camera active
i=1719  hp=0   goal=1  phase=0  flags=3  power=5   scene=2
final   scene=0                                               <- level exit completes
```

HP 50 → 20 in steps of 2 is exactly the registry's "15 hits". Every predicted transition appears:
flags gains 0x02 then 0x01, the power word gains 0x04, the goal latch reaches 1, the scene leaves 2.

### A check I wrote, that passed, and then deleted

The first version of the oracle asserted *"the goal latch is observed set while `0x80090BEE` is
still 0, therefore the exit does not depend on it"* — and it **passed**. It was unsound.
`sample()` issues several sequential RPC reads, so a frame boundary inside one sample yields a
**torn tuple**; the first run produced exactly that false ordering, and the static code shows the
true order is the opposite (camera start *precedes* the latch, same block, same frame). Runtime
polling cannot order two stores in one basic block, and a check that can pass for the wrong reason
is worse than no check — a lesson this project has banked before. It was replaced by an assertion that
the exit genuinely completes (scene leaves 2), with the ordering settled statically and the
independence settled by the exhaustive consumer census.

## Traced follow-up — the Interpreter re-take (same day)

The operator recorded `movies/Phase4/Interpreter/D16_Thumper_Defeat.movie.json` (4060 frames,
format v4, `armed_while_paused: true` so playback self-corrects the arm phase). Being
Interpreter-recorded, **arming is free** — `tools/phase4_d16_f03_trace.py` write-watches twelve
addresses and reports the actual writer PC for each. Ring not truncated (7,069 events), so the
negatives below are sound.

### The HP arc, at instruction level

`berry_tough_damage_dispatch` `0x800590E4` writes Thumper's HP **exactly 15 times**: 50 → 20 in
steps of 2. The registry's "15 hits" is no longer an inference from polling. Init to 50 is
`mover_init_from_record` `0x80049CA0`; the final 0 is the overlay's own
`level_completion_handler` `0x800B45AC`.

### The camera exit path never fires here

The flags word is written **three times in 4060 frames**: BIOS 0 → `2` by the camera start
`0x8004DB44` → `3` by case 1 `0x8004EB1C`. **Selector case 3 never runs.** The level ends with the
cinematic still active and the suppression bit still set. So the earlier "unobserved" is really
*"does not occur"* — case 3 belongs to cinematics that **return to gameplay** (the telescope path),
and the operator confirms this level has no telescope. The residual is closed as a negative, not
left open.

### `0x80082388` identified

201 writes, all from `contact_cursor_transition_reset` `0x80054AD4` (three sites) plus
`gameplay_state_reset_cursor_seed`. That function sits **immediately after** `four_byte_store`
`0x80054AAC` — the same subsystem the selector drives. `0x80082388` is that subsystem's
**transition countdown**, which is exactly what "wait for `[0x80082388] == 0` before completing
phases 1 and 3" means. Combined with the `(128,128,128,16)` / `(0,0,0,16)` call pattern and the fact
that three of `four_byte_store`'s four outputs are set-and-hold while the fourth (`0x8008248B`) is
rewritten 2,571 times, "screen tint/fade parameters + duration" is now well supported — though the
consumer is still untraced, so it stays *supported*, not *proven*.

### ⚠️ The archived "fight phase/attack counters" are refuted

The legacy Thumper note claims counters tick at `0x80090BF2` / `0x80090BF6`. Both are camera-block
`+0x32` / `+0x36` — immediately past the field this pass proved had been misattributed. The trace
settles it:

- **`0x80090BF6` — refuted outright.** Five writes, **every one from the BIOS** (`0xBFC02BB0`, bulk
  zeroing at load), all value 0. No game code writes it at any point in the movie.
- **`0x80090BF2` — real variable, wrong owner.** 44 writes; 38 from `gameplay_effect_spawner`
  `0x8005CD2C` (site `0x8005CE6C`), one from `plant_spawn`, the rest BIOS. It cycles 0/1/1/2 on a
  ~48-frame period *throughout* the movie, long before and after the fight. Nothing Thumper-specific.

**And it validates the declared blind spot.** The static census found **zero** stores to
`0x80090BF2`, yet 38 happened — it is written **through a pointer**, precisely the limitation both
scans declared and deliberately refused to claim a negative against. Had that caveat been dropped
for a cleaner-sounding result, this pass would have banked a false negative.

### Method correction: identify an overlay by writer PC, not by hashing it

The region-A head hash came back `UNRECOGNISED` at both sample points in this movie — **the overlay
mutates its own first bytes at runtime**, so hashing that window only identifies the blob shortly
after load. The poll-only oracle got a match purely because it sampled at playback index 3.

The robust check is the **writer PC**: a write to `0x800823A0` from `0x800B4190` can only happen if
the blob whose `0x800B4190` is `sh v0,0x23a0(at)` is executing — and that write is in the log. The
trace tool asserts identity that way; the hash is retained only as a weak signal.

### Not instrumented in this run

The operator also killed a mosquito and took hits from both Thumper and a mosquito (the mosquito
rises after landing its hit). None of that was watched — the watch set was scoped to the three open
questions — so nothing is claimed about it. The movie *does* contain the activity, so D16's
remaining "mosquito spawning" item needs a **new watch set, not a new recording**.

> **Retracted the same day.** This section first recorded a lead that "Hopper takes damage in the
> Council Chamber". The operator had misspoken and meant Thumper — this is the Thumper stage. The
> lead was never instrumented; it was banked from a chat remark, which is precisely what
> [[EXP_2026-08-03_phase4_e02_region_codes]]'s own lesson forbids ("inference from chat is NOT
> measurement"). Labelling it "not instrumented" was not enough to make it safe: it still reached
> four surfaces and a commit message before being caught.

## Fight phases + the mosquito (second traced pass, same movie)

`tools/phase4_d16_fight_static.c` (40/40 pins) + `tools/phase4_d16_fight_trace.py` →
`analysis/phase4_d16_fight.json`. Ring not truncated.

### The species dispatch

One pass over 64 slots at load (`0x8004A484..0x8004A6C0`): roster base `0x80094A38` stride `0x1C`,
actors stride `0x84`, species byte at roster `+0x0C`, species 6..41 dispatched through the jump
table at **`0x8001B264`**. Each arm sets a class byte and installs a **species callback at actor
`+0x7C`**.

> ⚠️ **The `+8` that changes every offset.** Stores are written against `s1 = actor + 8`, so
> `sw fp,0x74(s1)` is actor **+0x7C**, not `+0x74`. A first pass at this read the encoding literally
> and concluded `+0x74` — wrong by exactly 8, and it would have contradicted the archived note for
> the wrong reason. Cross-checked against the same function's HP store (`sh v0,110(t0)`, t0 = actor
> base = `+0x6E`, and Thumper's HP is `0x8009FE72` = `0x8009FE04 + 0x6E`), then confirmed live.

- **species 16 = Thumper** → arm `0x8004A5EC`, callback `0x8004A0F4` — **shared with species 22 and 36**.
- **species 10 = mosquito** → callback `0x8004A180`.

Live: `+0x7C` holds exactly those pointers, and is written **once**, by `0x8004A5F0` — the pinned
arm itself. The Council Chamber holds **one Thumper and two mosquitoes** (located by scanning RAM
for the pinned callback pointers, not by assuming an array base).

> **Correction to a long-standing shorthand.** The actor array base is `0x8009FD80`;
> **`0x8009FE04` is slot 1**, not the base. Phase-1 memory records `0x8009FE04` as "the" chunk-31
> base, which is why the first survey pass returned nothing. Derived here from Thumper's own roster
> pointer at `+0x80`, not assumed.

### Thumper has no fight-phase counter

His species callback `0x8004A0F4` is **40 bytes: `play_sound(26, actor+4)`**. Not a driver — the
identical shape to its neighbours, and **exactly the trap D18 already banked for Thud** ("+0x7C =
play_sound not a driver"). The census name `thumper_driver_cb` encodes the wrong assumption.

His behaviour is the shared mover-VM:

| field | role | writer | writes |
|---|---|---|---|
| `+0x70` | mover-VM IP, seeded to `0x80077634` (program table entry 9) | `0x8004C834` | 938 |
| `+0x6C` | VM **wait countdown** (0xf, 0xe, 0xd… every 2 frames) | `0x8004C1C0` | 266 |
| `+0x44` | action state, cycles 0/1/2 | `0x8004C110` | 25 |
| `+0x62` | set to 10000 on defeat | `0x800B45A4` (overlay) | — |

So "fight phases" is the wrong shape of question: the *structure* of the fight — when a mosquito is
thrown — lives in the **overlay**, not in Thumper's record.

### The mosquito throw is overlay code

`LEVEL02/LEVEL.BIN` `0x800B4330..0x800B43C0`: sets `+0x62 = 10000`, the target at `+0x0C`,
`+0x20 = -3072` (upward), the aim components `+0x1C`/`+0x24` from the angle table `0x80074970 >> 2`,
increments a **direction counter at `0x800B4940` that wraps at 4**, and plays sound 25. The
mosquito's VM IP is re-seeded to **`0x80077654`** — program table entry 10, the archived note's
"flight program". Observed live at frame 37516.

The species callback's one-shot then fires **exactly once**, at frame 37696: `0x8004A1D8` writes
`+0x6C = 25` and the two aim fields are doubled. That is the operator's *"the mosquito rises after
the hit"*, pinned to the instruction.

### Verdicts on the archived note

| claim | verdict |
|---|---|
| mosquito VM IP = `0x80077654` flight program | ✅ **confirmed** |
| species callback at `+0x7C` | ✅ **confirmed** (and my own first reading of `+0x74` was wrong) |
| launcher at `~0x80049C98..0x80049DB8` in `FUNC_800498AC` | ❌ **wrong** — that range is `mover_init_from_record` `0x80049C30`, the generic actor initializer. The launcher is overlay code. |
| Thumper's attack cycle runs in his species callback | ❌ **wrong** — it is a `play_sound(26)` wrapper |
| Thumper's program is park-in-place `0x800776AC` | ❌ **not what init writes** — init seeds `0x80077634` (entry 9). `0x800776AC` is the *pre-init* value, which is exactly how an early sample misleads (it misled this analysis too). |
| aim point at `+0x34/38/3c` | ✅ **confirmed** (see below — it was never a contradiction) |
| flags `0x0002 → 0x4007` | ✅ **confirmed** (second capture) |

Final scorecard: **three refuted, four confirmed** from one archived page. Every claim was
re-derived rather than cited, which is what made both the refutations and the confirmations worth
anything.

### Settling the two that were left undetermined

The first capture stored a flat 200 values per field against 1,562 writes on the flags word. That is
a **sampling gap, not a negative** — which is why it was recorded as undetermined rather than
refuted. The second capture stores *transitions* plus a full **distinct-value set**:

**`flags 0x0002 → 0x4007` — CONFIRMED.** The distinct set is
`0x0, 0x2, 0x5, 0x6, 0x7, 0x1007, 0x4002…0x4007, 0x5006, 0x5007`. Both `0x2` and `0x4007` are
present. Bonus: `0x1007` and `0x5007` show **bit `0x1000` set and then consumed** — the one-shot
request, visible in the value set exactly as the static reading predicted.

**The aim offsets — CONFIRMED, and never actually a contradiction.** Both sets are real and they are
*different things*:

| field | writes | writer | role |
|---|---|---|---|
| `+0x34`, `+0x3C` | 7 each | init, then the mover-VM on the **throw frame** | discrete **target/setpoint** |
| `+0x1C`, `+0x24` | 178 each | the overlay launcher | per-frame **launch velocity** |

This is the same two-field pattern [[EXP_2026-08-04_phase4_d16_f03_thumper_council_chamber]]'s
sibling row D17 already documented for the bird (AI setpoint vs interpolated position). My earlier
"the launcher writes `+0x1C`/`+0x24`" was *incomplete*, not wrong.

**And it explains the rise.** `+0x38` is the **vertical target**, and after the one-shot fires at
frame 37696 the **overlay** (`0x800B3E54`) walks it in steps of `0x800` —
`0xA2A0 → 0x9AA0 → 0x92A0 → 0x8AA0 → 0x82A0`. That is the operator's *"the mosquito rises after the
hit"*, at instruction level, and it is overlay-driven rather than part of the species callback.

### The `[0x800A6597] == 3` branch at `0x800B4158`

**Not taken — and the reason is measured, not guessed.** The index only ever holds **0 or 1** in this
run, never the 3 the branch tests for. The enemy quota was cleared by unrelated code
(`0x80046C10`/`0x80046C64`), not by that branch's store at `0x800B4164`. The branch's *effect* is
known statically; what remains unknown is **which berry/species index equals 3** — a question about
the index's domain, not about this branch.

## The arena — a number on the actor, not a place

`tools/phase4_d16_arena.py` → `analysis/phase4_d16_arena.json`.

There is no arena object, no trigger volume, and nothing in the bytecode. `random_dir_step`
(`0x8004C278`) recomputes the target from a **fixed anchor** every step:

```
s4           = [roster_record + 0x14] << 4        ; set once at 0x8004C194
angle        = 12 bits from the noise cursor 0x800822F4
[actor+0x34] = [actor+0x28] + (sin(angle) * s4) >> 9      ; X from anchor X
[actor+0x38] = [actor+0x2C]                               ; Y = anchor Y, untouched
[actor+0x3C] = [actor+0x30] + (cos(angle) * s4) >> 9      ; Z from anchor Z
```

Deriving from the anchor rather than from the current position is what makes it a **bounded
circle** instead of a drifting walk.

Measured for Thumper: `roster+0x14` = **25** → `s4` = 400; the sin table `0x80074970` has amplitude
**16384**; so max offset = `(16384 × 400) >> 9` = **12,800 units**.

| check | result |
|---|---|
| anchor X / Z writes during the fight | **none** — fixed at (4512, 3232) |
| anchor Y writes | 9, all from the overlay `0x800B400C` (`+= 4096`) — Thumper's hop |
| max observed target offset | **12,800.4** vs predicted **12,800** |

**So the arena is a fixed horizontal circle of radius 12,800 centred on (4512, 3232)**, and the
observed maximum *reaches* it — a real radius, not a loose upper bound. Vertical motion is a
separate, overlay-driven concern.

### Two read-timing errors, the same error twice

Both worth recording because they produced confident wrong answers, not obvious failures:

- **`roster+0x14` read 0.** Sampled 6 s in — **before `mover_init_from_record` runs at frame
  37025**. A post-run read was equally useless (playback had ended). Only a *mid-fight* pause gives
  25. This is the identical mistake that made `0x800776AC` look like Thumper's VM program earlier in
  this same investigation. The tool now arms at frame 0, runs into the middle of the fight, pauses,
  and reads there.
- **The sin amplitude.** I assumed 4096 (the usual 1.3.12 convention) and predicted 3,200 against an
  observed 12,800 — which made a *correct* model look refuted. The table is 1.2.14, amplitude
  16384. The tool now **measures** the amplitude from the live table instead of assuming it.

Assuming a constant and assuming a sample point are the same class of error: an unstated premise
doing load-bearing work.


## Residuals

- The mosquito aim-offset discrepancy (`+0x34/38/3c` vs the measured `+0x1C/+0x24/+0x20`) and the
  `flags 0x0002 → 0x4007` claim are both undetermined; the flags value list needs an uncapped
  capture to settle the second.
- Whether other actors' `roster+0x14` values give a per-species arena table (only Thumper's was
  read). Cheap, but not needed for this row.
- `four_byte_store` `0x80054AAC` writes four byte globals (`0x80082362`, `0x8008248A`,
  `0x8008241E`, `0x8008248B`) from `(a0,a1,a2,a3)`, called `(128,128,128,16)` and `(0,0,0,16)`.
  **Narrowed by the trace** to the `contact_cursor_transition_reset` `0x80054AD4` subsystem; three
  outputs are set-and-hold, the fourth is rewritten every frame. "Screen tint/fade + duration" is
  now well supported but the consumer is untraced — still *supported*, not *proven*.
- ~~`[0x80082388]` unidentified~~ — **CLOSED by the trace**: it is the transition countdown owned by
  `contact_cursor_transition_reset` `0x80054AD4`.
- ~~The camera exit path (case 3) was never observed~~ — **CLOSED as a negative**: it never fires in
  this scene at all; it belongs to cinematics that return to gameplay.
- The extra branch at `0x800B4158` gated on `[0x800A6597] == 3` (the index [[SYS_berry_projectile_and_homing]] and E14 use against the
  side table) clears the enemy quota `0x800A658E` and makes two further calls. Not
  characterized.
- Neither *static* scan can see an access through a pointer loaded from memory. That is stated, not
  claimed against — and the trace **proved the caveat was load-bearing**: `0x80090BF2` has zero
  static stores and 38 real ones.
- D16's other `missing` items — phases, mosquito spawning, arena/objective — are untouched by this
  pass.

## Reproduce

```
cc -O2 -std=c11 -Wall -Wextra -Werror tools/phase4_d16_f03_static.c -o /tmp/d16 && /tmp/d16
tools/phase4_d16_f03_census.py                       # second implementation + artifact
tools/phase4_d16_f03_oracle.py --port 23665          # live, poll-only
tools/phase4_d16_f03_trace.py --port 23672              # traced, Interpreter movie
cc -O2 -std=c11 -Wall -Wextra -Werror tools/phase4_d16_fight_static.c -o /tmp/d16f && \
    /tmp/d16f REBUILD/files/SCUS_942.88                 # species dispatch pins
tools/phase4_d16_fight_trace.py --port 23685           # fight phases + mosquito
pytest tests/test_phase4_d16_f03.py -q
```
