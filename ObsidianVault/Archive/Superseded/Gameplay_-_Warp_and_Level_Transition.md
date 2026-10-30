---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Gameplay - Warp and Level Transition.md
aliases:
  - "Gameplay - Warp and Level Transition"
migration_action: convert_to_canon
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Gameplay - Warp and Level Transition.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Gameplay_-_Warp_and_Level_Transition.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Gameplay - Warp and Level Transition
type: core
updated: 2026-06-20
tags: [core, gameplay, warp, transition, milestone6, gap-0035, b8]
---

# Gameplay — Warp & Level Transition (GAP-0035 static model)

> Advances [[Gap Audit|GAP-0035]] via the `current_scene_id` xref ([[MEM - Event System Globals]]). **`current_scene_id` (`0x80082504`) is the single central transition variable** — writing it re-points **both** the scene event-handler **and** resource loading. All STATIC (EXE-read, `tools/exe_read.py`); live warp execution remains unproven (local-only, GAP-0001).

## Static model
`current_scene_id [0x80082504]` is set by a writer, then consumed by two independent subsystems each tick / at load:
1. **scene-handler selection** — the dispatch caller `0x8004f038` (in `gameplay_state_machine`) reads `scene_id` and `jr [0x8001b4fc + (scene_id−1)·4]` → the per-scene overlay verb ([[Gameplay - Events and Triggers]]). Scene 1 → the scripted-spawn sequencer `0x800b3bb8`.
2. **resource loading** — the loaders in `0x8003axxx` (the LEVEL.RAW/stream loader [[FUNC_8003A318]] region) **read `scene_id`** (xref: `0x8003a54c/748/81c/968/9c0/ab48/abf0`, `0x8003dd50`, `0x8003e4e4`, `0x8003f510/540`); the stage loader [[FUNC_8003CF2C]] is called with the stage and dispatches per-stage via table `0x8001afb0`.

⇒ **Answer to "does warp change handler selection, resource loading, or both": BOTH** — they share `0x80082504`.

## Writers of `current_scene_id` (10, decoded)
| Writer | Region | What it stores |
|---|---|---|
| `0x8004fd0c` | shell SM `0x8004fa40` | `scene_id = scene_table[idx]` — **`lw v0,0x7fa0(0x8007…)`** = the scene-id table `0x80077fa0` `{0x11,1,3,2,6,0xa,0xb,4}` (level-select/sequence) |
| `0x80052274` | **orchestrator [[FUNC_8005222C]]** | `scene_id = 19` — the **"loading" scene**; immediately loads global/common resources via `0x8003cf2c(19)` (CORRECTED: was guessed "computed target") |
| `0x80052314` | orchestrator | `scene_id = 0` (clear, mid-transition; precedes the `0x8003f2f0 ×40` clear loop) |
| `0x80052474` | orchestrator | `scene_id = s8` — **restores** the saved target (read into `s8` at entry), after finalizer `0x80045a60` |
| `0x8003f524` | loader `0x8003f5xx` | `scene_id = 18` (fixed; near the FMV/MEMORY.BIN overlay loaders) |
| `0x8004fdc0/fde4`, `0x800503ac/e0` | shell SM | transition bookkeeping (set/reset) |

## State variables
- **`0x80082504` `current_scene_id`** — the lever (CONFIRMED). **Hot per-frame dispatch key in gameplay (read ~15×/frame) — immutable during play; mutating mid-gameplay crashes** ([[Experiment - In-game warp trigger]]).
- **`0x800822fc`** loaded-stage / `[gp+0x564]` — the *currently-loaded* stage vs the *requested* `scene_id` ([[Finding - Level-warp mechanism]]).
- Substate `[0x8008243c]` (`main_shell_substate`) — shell-SM dispatch `jr [0x8001b3c4+sub*4]`; substate **5** = load case → orchestrator. (Forcing substate=5 **alone** is harmless; the old finding's crash was its `scene_id` half.)
- **`[0x8008245c]`** scene-table **index** — the **safe pre-latch selection source**: `scene_id = scene_table[ [0x8008245c] ]` (`scene_table @ 0x80077fa0`). Set by shell-SM substate handlers + front-end overlay.
- **`[0x8008224e]`** gameplay↔shell **gate** — `==0` gameplay loop `0x8004ecd4`; `!=0` shell/menu `0x8004f478` (→ substate machine → orchestrator). The gameplay→shell handoff lever (6 writers; only `0x8004f3ac` sets non-zero).
- **`[0x800823a0]`** **transition-state lever** (the native TRIGGER) — set by resident initiators `0x800496d8`(1)/`0x8004a8b4`(2)/`0x8004b3c0`(6) (called by overlay scene verbs on level-exit); `=6` reproducibly initiates the native gameplay→shell→scene-init sequence ([[Experiment - In-game warp trigger]]). The fade handler `0x8004f230`-region progresses it (→3→4) + tears down the level before the gate flips. Companion: fade color `[0x80082470]`.

## Relationship to event dispatch
Direct: the **same `scene_id`** that the warp orchestrator writes is what the per-tick dispatcher reads to pick the scene handler. So a warp **changes which event/update verb runs** — events and warp are one system keyed on `0x80082504` ([[MEM - Event System Globals]]).

## Relationship to resource loading
The loaders (`0x8003axxx`, [[FUNC_8003A318]] / [[FUNC_8003CF2C]]) read `scene_id` → load that stage's LEVEL.DAT/LEVEL.RAW/overlays ([[Core - CD Streaming and Caching]], [[Asset - Disc file map]]). The fixed `scene_id=18` writer near the FMV loaders (`0x8003f524`) suggests scene 18 = a non-level state (front-end / FMV), consistent with the scene-id table.

**Per-stage loader dispatch (STATIC, EXE-read):** [[FUNC_8003CF2C]] does `jr [0x8001afb0 + (stage−1)·4]` over a **17-entry table** of per-stage loader handlers (`0x8003cfc4 … 0x8003d1bc`, all resident; `[15]/[16]` = `0x8003cfc4` default; `[17]=0` terminator). The streaming loader [[FUNC_8003A318]] **reads `scene_id` 7×** (`0x8003a54c/748/81c/968/9c0/ab48/abf0`) to pick per-stage resources/LBAs. **`G_DAT_BASE_PTR` (`0x80082498`) is set once** at `0x8003d4ac` to the loaded LEVEL.DAT buffer — the per-stage load result the event/DAT stream then walks ([[Gameplay - DAT Event Stream]]).

## Scene-init gameplay-state reset (GAP-0035 substep, 2026-06-20)
The shell/main state machine `0x8004fa40` — the same function that writes `current_scene_id` — calls **[[FUNC_8005B714]]`(current_scene_id)` @ `0x8004fdf0`** (`… sw scene_id; lw a0,scene_id; jal 0x8005b70c; bne v0,…`). That callee is the **gameplay-state reset**: it zeroes the `0x80082xxx` state cluster, **seeds the shared byte-stream cursor `0x800822f4` to the resident noise table `0x80017DB4`** ([[Gameplay - Resident Event Stream]]), **and SPAWNS THE PLAYER** — at `0x8005baa4` it `jal`s the spawn fn [[FUNC_80046B20]]`(player, scene_id)` (`a1 = s2 = a0 = scene_id`), runtime-confirmed 2026-06-20 ([[Experiment - Initial spawn write-watch]]). Once per stage entry (init-once guard `0x800822f8`). ⇒ scene transition re-points handler + resources **and** resets gameplay state + re-seeds the noise cursor **and places the player** from the resident start table `0x80077314[scene_id]`. (Live-warp execution still unproven — this is the static init path the SM runs on entry; the spawn step was byte-proven via the LEVEL01 cold-boot watch.)

## Transition orchestrator [[FUNC_8005222C]] — decoded (2026-06-20, static)
The shell SM enters its load case (substate `[0x8008243c]=5` → `0x8004fca0`) and `jal`s **`0x8005222c`** (callers `0x8004fca8`, `0x8005028c`). Decoded sequence (bounds `0x8005222c..0x800524b8`, 163 instrs):

1. **Save target** `s8 = [0x80082504]` (the requested scene/stage).
2. **`scene_id = 19` (loading scene)** → **load global/common resources** `0x8003cf2c(19)` ([[FUNC_8003CF2C]]) + `0x80046ac0(21)`.
3. **Resource-select + screen-fade loop** (`s1=1..16`): `0x8003a314` (selector, ≈[[FUNC_8003A318]]) + fade `0x80054aac/0x80054ad4` (RGB `128`→`0`); inner `0x8003f2f0 ×40`.
4. **Scroll reset** `0x8003df14(0,−8)` ([[FUNC_8003DF14]]) + **`scene_id = 0`** + clear state halfwords `0x80082388/2494/2430`.
5. **Finalize** `0x80045a60()` ([[FUNC_80045A60]] — clears flag `0x80082478`, resets two `0x8006dxxx` subsystems).
6. **`scene_id = s8`** (restore target) → return status.

⇒ **Transition sequence (prose):** *shell-SM load case → orchestrator: fade out → swap scene_id to 19 → load global resources → per-step resource select + clear → reset scroll/state → finalize subsystems → restore scene_id=target → return.* The **target stage's own files** are loaded by a **separate** `0x8003cf2c(scene_id)` call from shell-SM caller `0x800503cc` ([[FUNC_8003CF2C]] has 4 callers: `0x8003f544/0x800503cc/0x80052290/0x8005b830`); the scene-init reset [[FUNC_8005B714]]`(scene_id)` zeroes the state cluster + reseeds the noise cursor.

## Player placement / spawn state → [[Gameplay - Player Spawn and Placement]]
The orchestrator `0x8005222c` and both callees (`0x8003df14`, `0x80045a60`) write **no** player-position global (`0x800a6500/04/08`) — verified `--store-ea`. **Player placement is a SEPARATE 3-layer system** (decoded 2026-06-20):
1. **Initial level-load spawn = warp landing** ([[Gameplay - Initial Player Spawn]]) — **[[FUNC_80046B20]]`(player, scene_id)`**, called from scene-init [[FUNC_8005B714]], sets the live position from the **resident EXE start table `0x80077314 + scene_id*12`** (word0→X, word1→Z, word2→heading; Y computed). **Runtime-CONFIRMED** for the cold LEVEL01 spawn ([[Experiment - Initial spawn write-watch]]) **AND for non-LEVEL01 warp landings** — diverting the cold boot to scene 3/6/2/4 calls this fn with `a1`=that scene and lands cleanly at table[scene] ([[Experiment - Warp landing diversion]], 2026-06-21). The cold initial spawn and a warp landing are **one code path**; only per-level values differ. Overturns the earlier LEVEL.DAT/LEVEL.BIN-baked guess. (Not in the *orchestrator* path, but inside scene-init, which runs on every scene entry.)
2. **Checkpoint-save [[FUNC_80054C90]]** (gameplay loop) — distance-gated snapshot of live pos → **respawn anchor `0x800a6550/54/58`** + flag.
3. **Respawn restore [[FUNC_8005B134]]** (death/respawn states) — anchor → live pos + previous-pos copy + full velocity/flags reset.

**Clean separation of GAP-0035 concerns:**
| Concern | Owner |
|---|---|
| Resource loading | [[FUNC_8003CF2C]] (global id 19 + target `scene_id`) + [[FUNC_8003A318]] |
| Scene-ID selection | `current_scene_id 0x80082504` (orchestrator 19→0→target) |
| Gameplay-state reset | [[FUNC_8005B714]] (zeroes `0x80082xxx` cluster + seeds noise cursor) |
| **Player placement** | **level-load spawn → [[FUNC_80054C90]] checkpoint-save → [[FUNC_8005B134]] respawn** (NOT the orchestrator) |
| Live-warp verification | shell-phase fixture (runtime, GAP-0001) |

## What a warp does (GAP-0035 summary)
| Effect | In warp? | Where |
|---|:--:|---|
| Reload resources | **YES** | `0x8003cf2c(19)` global + `0x8003cf2c(scene_id)` target + `0x8003a314` selector |
| Reseed gameplay state | **YES** | orchestrator clears `0x80082xxx`; [[FUNC_8005B714]] zeroes cluster + reseeds noise cursor |
| Change scene-handler | **YES** | `scene_id` → `jr [0x8001b4fc + (scene_id−1)·4]` |
| Screen fade | **YES** | `0x80054aac/0x80054ad4` |
| Scroll/background reset | **YES** | [[FUNC_8003DF14]] |
| Subsystem/audio finalize | **YES** | [[FUNC_80045A60]] |
| Move player | **YES (via scene-init)** | [[FUNC_8005B714]] → [[FUNC_80046B20]]`(player, scene_id)` from resident table `0x80077314` — NOT the orchestrator; **landing CONFIRMED live for scene 3/6/2/4** ([[Experiment - Warp landing diversion]]) |

## Fade RENDER mechanism (how the screen actually darkens) — 2026-07-01, gp0Trace
The in-gameplay fade level `[0x80082388]` (`gp+0x5f0`, `prog`) is drawn as a **single full-screen GP0 `0x62` rectangle** — monochrome, semi-transparency **mode 2 (B−F, subtract)**, position (0,0), size 512×240, color `(128−prog)*2` (clamped 0..255) — built each frame by the resident **fade-rect builder `FUNC @0x80028d74`** (reads `[gp+0x5f0]`, `[gp+0x6fc]`, `[gp+0x698]`; sets W/H/color at prim buffer `[0x8008249c]`; links it into the SCENE ordering table at its **front bucket** so it draws LAST, over everything incl. the HUD). The mode-2 texpage is set by the `0xE1` immediately before it (e.g. `0xe1000640` → STP bits = 2). As `prog` falls 128→0 the subtract term grows → the whole composited frame darkens to black; `prog` 128 = no subtract (full bright). Other readers of `[0x80082388]`: the lerp `0x80054ad4` (updates it toward target color `[0x80082362]`) and `0x8004d74c`. **This is the primitive the Tier-3 render cave's `suppress_terrain` was wrongly collapsing** (it classed all `0x60..0x7f` as decor) → no fade in/out on the custom-level disc ([[Tier 3 - Custom Level Bugs]], fixed 2026-07-01).

## Evidence & confidence
- Orchestrator `0x8005222c` decoded (scene_id 19→0→target; global load; fade; reset; finalize) — **CONFIRMED (static, decoded)**.
- Callees `0x8003df14` (scroll/offset helper) + `0x80045a60` (finalizer/subsystem reset) — **CONFIRMED (decoded); purpose LIKELY**.
- The **orchestrator** `0x8005222c` does NOT move the player (no player-pos writes) — **CONFIRMED**; placement happens in **scene-init** [[FUNC_8005B714]] → [[FUNC_80046B20]] instead (runtime-confirmed).
- `scene_id` written by warp-orch `0x8005222c` + shell-SM table + loader — **CONFIRMED (static, decoded)**.
- Scene-init [[FUNC_8005B714]]`(scene_id)` = state reset + cursor seed + **player spawn** ([[FUNC_80046B20]], from `0x8004fdf0`) — **CONFIRMED (static decode + runtime write-watch)**.
- `scene_id` read by dispatcher + loaders → drives both handler + resources — **CONFIRMED (static xref)**.
- The full warp control-flow (orchestrator internals, the `0x8003df14`/`0x80045a60` callees) — **partially decoded** (the [[Finding - Level-warp mechanism]] chain). **Warp LANDING now executed live** (cold-boot diverted to scene 3/6/2/4, no crash — [[Experiment - Warp landing diversion]]); an **in-game (mid-level) orchestrator warp** via `0x8005222c` is still crash-prone.
- **Warp-landing capture — DONE (runtime 2026-06-21):** [[Experiment - Warp landing diversion]] confirmed scene-init [[FUNC_8005B714]] → [[FUNC_80046B20]]`(player, scene_id)` lands cleanly at table[scene_id] for scene 3/6/2/4 (`spawn a1` = the scene index, `src s0 = 0x80077314 + index*12`). **Index = `current_scene_id [0x80082504]` = level-select value `scene_table[idx]`; `scene_id == stage`.** Cold spawn and warp landing are one code path. **Clean lever:** poke `scene_table[1]` (`0x80077fa4`) before the cold-boot scene_id write (frame ~3486); a *late* `[0x80082504]` poke crashes (index latched at scene-init entry — the [[Finding - Level-warp mechanism]] wall, now explained).

## In-game warp TRIGGER — shell-vs-gameplay architecture (2026-06-21, runtime) → [[Experiment - In-game warp trigger]]
Decoded the path *into* the orchestrator/spawn (the trigger half) and why mid-gameplay forcing crashes:
- **Per-frame top loop (`0x8004fe70`) gates on `[0x8008224e]`:** `==0` → gameplay loop `0x8004ecd4` (+ dispatcher [[Gameplay - Events and Triggers|0x80054964]]`(scene_id)`); `!=0` → shell/menu handler `0x8004f478` → shell SM substate machine → **substate 5 → orchestrator [[FUNC_8005222C]]**. The shell SM dispatches by substate `[0x8008243c]` (`jr [0x8001b3c4+sub*4]`); the **safe pre-latch selection** is `[0x8008245c]` (scene-table index) → `scene_id = scene_table[idx]`.
- **Orchestrator is shell-only:** `execTrace 0x8005222c` = **0 hits during cold boot** (cold uses the substate-0 path); 0 during gameplay (gate=0). Its 2 callers (`0x8004fca8` substate-5 a0=1; `0x8005028c` a0=0 gated on `0x8009b888` bit0) are both shell-phase.
- **Why mid-gameplay `scene_id` pokes crash (CONFIRMED, reproduced):** `scene_id [0x80082504]` is read **~15×/frame** by gameplay+overlay consumers; mutating it mid-play → wrong dispatch → **BIOS crash `0xbfc02bac`**. Isolation: forcing **substate=5 alone** or **gate=1 alone** does **NOT** crash — so the old "clean lever" crashed on its `scene_id` half, not substate. **Precondition: `scene_id` is immutable during gameplay; only the shell phase may change it.**
- **Gate `[0x8008224e]` writers (6):** only `0x8004f3ac` sets it non-zero (gameplay→shell, in the shell handler after finalizer `0x80045a60`); the rest set 0 (→gameplay), incl. scene-init `0x8005b898` at load-complete.
- **NATIVE TRIGGER LEVER — CAPTURED 2026-06-21 (max effort):** the trigger is the **transition-state var `[0x800823a0]`**, set by resident initiators **`0x800496d8` (type 1) / `0x8004a8b4` (type 2) / `0x8004b3c0` (type 6)** (each + fade color `[0x80082470]` + helpers). The overlay never writes `[0x800823a0]` (0 overlay writers) ⇒ the **per-scene overlay verbs call these resident initiators** on a level-exit. Poking `[0x800823a0]=6` from gameplay (`level02.sav`) **reproducibly initiates the native gameplay→shell-SM→scene-init [[FUNC_8005B714]]`(a0)` sequence** (frame 39547, ra `0x8004fdf8`); types 1/4/5/7/8/9 crash (omit companion state), 2/3 inert. The fade handler (`0x8004f230`-region) then progresses the fade + tears down the level (`[0x800822f8]→0`) before the gate flips. → [[Experiment - In-game warp trigger]].
- **Clean level→level *landing* residual:** the forced type-6 destination resolves to **scene 16** (a non-level/map scene; `scene_id` written at `0x8004fdc4`=`scene_table[idx]` or forced to 16 at `0x8004fde4`) → scene-init(16) crashes (`0xbfc02bb8`, no prepared resources). Poking `[0x8008245c]`/`[gp+0x4c4]` didn't redirect it. ⇒ the overlay verb's destination + resource setup is the **GAP-0033** residual; the *trigger lever* is captured, the clean *destination* is not.

### Pass-3 (2026-06-21) — overlay verb decoded + initiator model corrected → [[FUNC_8004A700]] / [[FUNC_8004ABF4]]
- **The three "initiators" `0x800496d8/a8b4/b3c0` are `sh [0x800823a0]` STORE-PCs**, inside enclosing fns `0x80048138` (type1) / **`0x8004a700`** (type2) / **`0x8004abf4`** (type6). No site `jal`s the store-PCs.
- **Overlay verbs call the initiators — PROVEN (was inferred):** `0x8004a700` is `jal`'d from overlay scene verbs `0x800b3e94` (LEVEL06, = scene-3 verb `0x800b3e88`+0xc) and `0x800b4ae0` (LEVEL04). Scene-3 verb `0x800b3e88` → `FUNC_8004A700(a3=3)` — **`a3` carries an explicit destination** for the type-2 path; the type-6 path carries none.
- **Type-6 is a PER-TICK updater, not a one-shot (RUNTIME-corrected, LOCAL-ONLY):** the native gate `0x8004f0e8` (`[0x800a657c]==0 && [0x800a6594]≥0`) is **OPEN during normal play**; `0x8004abf4` runs **every tick** on actor `[0x80090748]` (NULL mid-level → early-exit). The type-6 commit is a dormant countdown `[0x8008223c]`→5 (gated by `[0x8009b889]&0x20==0 && scene_id!=16`). ⇒ `[0x800a657c]/[0x800a6594]` are a *transitions-allowed* precondition, **not** the exit trigger (corrects the earlier static guess).
- **Destination resolution `0x8004fda0` (decoded):** `dest = scene_table[ [0x8008245c] ]` (`@0x80077fa0`), **forced to scene 16 when `[0x8008225c]!=0`** (map/results override; `scene_table[16]=0xffffffff`, so 16 only comes from the force-flag). `[0x8008245c]` is written by **7 sites, ALL in the shell SM** — never gameplay/overlay ⇒ a forced gameplay-side `[0x800823a0]=6` cannot supply a valid destination/resources → scene-16 crash. **Clean in-game level→level remains blocked on this shell-phase destination + orchestrator resource sequencing** (GAP-0033). Not achieved this pass.
- **Shell-SM destination writers ENUMERATED (static, EXE-read 2026-06-21) → [[Menu and HUD structure]] §4a:** 5 of the 7 `[0x8008245c]` writers are the **substate-machine handlers** `0x8004fc3c/50/64/78/8c` (dispatch `jr [0x8001b3c4 + [0x8008243c]*4]`), each latching a fixed destination index {1,11,2,7,12} → `scene_table` = scenes {1,12,3,4,13}; substate 5 (`0x8004fca0`) runs orchestrator [[FUNC_8005222C]]`(1)`. `scene_table[16]=0xffffffff` is read here directly — concretely **corroborates that the destination is shell-authored to constants, not gameplay-pokeable** (the GAP-0035B terminal reframe). The remaining 2 writers are the substate-var/other shell paths (`0x8004fad4/fca4/fcd4/fce8` write the substate selector `[0x8008243c]`).

### Pass-4 (2026-06-24, runtime) — `FUNC_8004ABF4` proximity math decoded; exit lead RULED OUT
- **`FUNC_8004ABF4` proximity test (CONFIRMED math):** the type-6 per-tick updater computes the **squared
  distance between Flik and the watched actor `[0x80090748]`** and tests it against a radius:
  actor pos = base `+4/+8/+0xc` (s32) **plus** per-tick sub-offset `+0x64/+0x66/+0x68` (s16); Flik
  `0x800a6500/04/08` with **Y compared as `Y−7360`**; trigger when
  `dist² < (radius[+0x6a]+250)²` **and** `[+0x6c] ≥ 0`. Decoded to C in `src_re/proximity_updater_8004abf4.c`.
- **RULED OUT as the LEVEL01 exit (negative result).** In LEVEL01 `[0x80090748] = 0x8009fd80`, a **MOVING NPC**
  (base X drifts 85788→89015→91644 while Flik idles) — not a fixed exit point. Teleporting Flik onto it flipped
  `[0x800823a0] 0→2`, which *looked* like the exit, **but advancing showed Flik FELL (Y→+51772) and RESPAWNED
  at spawn (197091,2734,492897), scene unchanged** ⇒ that `=2` was a **DEATH-FROM-FALLING respawn**, not a level
  exit, and is not attributable to `FUNC_8004ABF4`.
- **METHOD TRAP (record this):** *teleport-Flik-to-a-guessed-XZ is confounded by death-from-falling* — a
  non-floor landing makes Flik fall → `[0x800823a0]` sets → respawn. So **"Flik reaches position X ⇒ transition
  lever set" is NOT evidence of an exit.** The §10 exit-trigger position is **still 🔴 OPEN**; pursue an at-exit
  operator save (write-watch `[0x800823a0]`/`[0x8008245c]`) or the static decode of scene-1 verb `0x800b3bb8`.

### Pass-5 (2026-06-24, runtime — operator at-exit save) — the EXIT TRIGGER is a COLLISION-SECTOR region code ✅
The §10 "where does the level exit fire" question is **SOLVED**, using `level01_end_of_stage.sav` (Flik just
short of the exit). RE C: `src_re/level_exit_trigger.c`. It is **not** the type-6 `FUNC_8004ABF4` path (Pass-4,
ruled out) — it is a **static per-sector region code in the collision sector table**:
- **Query:** the scene/exit handler `FUNC_80048138` calls **`FUNC_80038f38(0, &Flik[+0x82])`** → returns
  `SECTOR_TABLE[ [0x80090560] ] + 0x2e` (the current sector's region code), **gated by `[Flik+0x82]==1`**.
  `SECTOR_TABLE = 0x800a7e48`, stride `0x30`; `[0x80090560]` = player's current collision sector.
- **Dispatch:** `FUNC_80048138` switches on the code → **code 2 ⇒ `[0x800823a0]=1`** (type-1 exit) + fade
  `[0x80082470]=23` + `FUNC_80050994(58)` (level-complete SFX). Codes 1/3/4 = other transition kinds (other
  levels; code 1 → `jal FUNC_8004A700` type-2).
- **Position:** LEVEL01 has exactly **one** sector tagged code 2 → **collision sector 177**, origin runtime
  `(-163008,-169888,-124832)`. "Where Flik must stand to end the level" = inside sector 177.
- **Disc source (static):** LEVEL.RAW **chunk-32** sector records (decompressed local `0x36570`, global
  `0xCD248`, stride `0x4c`; origin `+0x08/0c/10` = runtime`>>5`); **region code @ `+0x2c` (word) → runtime
  `+0x2e`**. Record 177 (global `0xD06D4`) has `+0x2c=2`, unique among the 189 real records. Editable via
  `tools/edit_collision_sector.py` + `tools/build_autolayout_disc.py`.
- **In-game proof:** walk forward from the at-exit save → lever `0→1` (writer PC `0x800496dc`) in sector 177 →
  **level torn down** (`[0x800822f8] 1→0`, `scene 1→0`), Flik did NOT respawn — a real transition. The stall at
  scene=0 afterward is the GAP-0035B handoff limit (next-level load is shell-authored), not a trigger flaw.

## Remaining unknowns / next actions
- ~~Orchestrator internal flow + `0x8003df14`/`0x80045a60` roles~~ **— DONE.** ~~Player-spawn writer + non-LEVEL01 landing~~ **— DONE.** ~~Orchestrator `a0` selector~~ **— DONE** (`0x8004fca8` a0=1 substate-5; `0x8005028c` a0=0 gated on `0x8009b888`).
- ~~Native in-game warp trigger LEVER~~ **— CAPTURED 2026-06-21** (transition-state `[0x800823a0]`=6 → native scene-init; above / [[Experiment - In-game warp trigger]]).
- **Residual (GAP-0033):** the per-scene **overlay verb** (`0x80054964` → `0x800bxxxx`) level-exit *condition* + its destination/resource setup — so a native exit lands in a real next level (not the forced-context scene 16). Decode the dispatcher verb that calls the resident transition-initiator `0x800496d8/a8b4/b3c0`.

## Related
[[Gameplay - Initial Player Spawn]] · [[Experiment - Initial spawn write-watch]] · [[Experiment - Warp landing diversion]] · [[Experiment - In-game warp trigger]] · [[FUNC_8005222C]] · [[FUNC_80046B20]] · [[FUNC_8005B714]] · [[MEM - Event System Globals]] · [[Gameplay - Events and Triggers]] · [[Finding - Level-warp mechanism]] · [[FUNC_8003CF2C]] · [[FUNC_8003A318]] · [[Core - CD Streaming and Caching]] · [[Asset - Disc file map]] · [[DuckStation Fork Reproducibility]] · `tools/trace_initial_spawn.py` · `tools/trace_warp_landing.py` · `tools/trace_shell_warp.py` · `tools/exe_read.py`
