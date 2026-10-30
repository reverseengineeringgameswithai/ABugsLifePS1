---
kind: experiment
id: Experiment_-_In-game_warp_trigger
created: 2026-07-08
updated: 2026-07-08
status: legacy_imported
confidence: confirmed
legacy_source: ObsidianVault/Experiments/Experiment - In-game warp trigger.md
aliases:
  - "Experiment - In-game warp trigger"
---

# Experiment — in-game warp trigger / shell-vs-gameplay architecture (GAP-0035 trigger half)

> Migrated from `ObsidianVault/Experiments/Experiment - In-game warp trigger.md` during the 2026-07-08 vault completion pass. Original action: `convert_to_experiment`. Reason: Experiment note should preserve proof artifacts and link Canon claims it validates.

# Experiment — in-game warp trigger / shell-vs-gameplay architecture (GAP-0035 trigger half)

> The landing/spawn is already proven ([[Experiment - Warp landing diversion]]). This note attacks the remaining half — the **native in-game (mid-level) warp TRIGGER** and the role of orchestrator [[FUNC_8005222C]]. **Pass-1 (commit 8daef4e): bounded** — orchestrator shell-only, gameplay↔shell gate `[0x8008224e]`, `scene_id` immutable in gameplay. **Pass-2 (max effort, below): the native trigger LEVER is CAPTURED** — the **transition-state var `[0x800823a0]`** (set by resident initiators called from the per-scene overlay verbs); poking it `=6` from gameplay reproducibly initiates the native **gameplay→shell-SM→scene-init `FUNC_8005B714(a0)`** sequence. A fully-clean level→level *landing* still needs the overlay's exit setup (destination + resources) — GAP-0033. **Pass-3 (2026-06-21): the overlay verb is DECODED** — the type-2 initiator `0x8004a700` is `jal`'d from overlay scene verbs (e.g. LEVEL06 scene-3 `0x800b3e88`, with destination arg `a3`); the type-6 path `0x8004abf4` is a **per-tick updater** (runtime-corrected) carrying no destination; the destination is shell-resolved at `0x8004fda0`. Runtime, local-only ([[DuckStation Fork Reproducibility]] / GAP-0001). Driver: `tools/trace_shell_warp.py` (`boot`/`loops`/`crash`/`trigger`); static: `tools/exe_read.py`.

## Pass-2 (2026-06-21, max effort) — native trigger LEVER captured
**The native transition trigger is the transition-state var `[0x800823a0]`.** Static `--store-ea 0x800823a0`: its only resident writers are gameplay-region functions **`0x800496d8` (type 1), `0x8004a8b4` (type 2), `0x8004b3c0` (type 6)** — each sets `[0x800823a0]` to a type code + a fade color `[0x80082470]` + calls helpers (`0x80050994`/`0x8005044c`). The overlay itself never writes it (0 overlay writers), so the **per-scene overlay verbs call these resident initiators** on a level-exit/win condition. The resident **fade handler** (`0x8004f230`-region, runs each frame) then progresses the transition (sets `[0x800823a0]`→3→4, lerps scroll `[0x80082388]`→128 via `0x80054ad4`) and, once the level is torn down (`[0x800822f8]==0` && `[0x8008216c]==3` && `[0x80082388]==128`), flips the gate `[0x8008224e]`→shell at `0x8004f3ac`.

**Capture (`tools/trace_shell_warp.py trigger`, from `level02.sav` scene 3; reproduced 2×):**
| `[0x800823a0]` poked | outcome | scene-init `a0` |
|---|---|---|
| 1 | CRASH `0xbfc02bb0` (needs companion state) | — |
| 2, 3 | inert (consumed by the fade handler) | — |
| **6** | **transition → scene-init `FUNC_8005B714(a0=16)`** (frame 39547, ra `0x8004fdf8`), pc `0x8006521c` | **0x10** |
| 4, 5, 7, 8, 9 | CRASH `0xbfc02bxx` | — |
⇒ **type-6 (`0x8004b3c0`'s type, the level-exit transition) reproducibly engages the native gameplay→shell-SM→scene-init path** — the actual native trigger mechanism, via the proper pre-latch transition-state lever (NOT the unsafe raw `scene_id` poke). Other types crash because poking `[0x800823a0]` alone omits the companion fade-color/flags/helper state the resident initiator sets.

**Destination / why it still crashes ~800f later:** with type-6 the shell SM selects the destination (`scene_id` written at `0x8004fdc4` = `scene_table[idx]`, or forced to **16** at `0x8004fde4` when `[gp+0x4c4]≠0`). In the forced raw context the destination resolves to **scene 16** — a non-level (map/results) scene with no prepared resources/spawn table entry — so scene-init(16) → BIOS memset crash `0xbfc02bb8`. Poking the index `[0x8008245c]` / clearing `[gp+0x4c4]` did **not** redirect it (the destination selection is overlay/menu-driven). ⇒ **a clean level→level landing needs the overlay's level-exit setup** (which selects the real destination + preps resources) — GAP-0033/0036. The player block was NOT re-spawned (X stayed `-16896`), consistent with scene-16 being invalid.

**Negative results (rule out resident-only capture):** grain `[0x800a65a1]=50` does not trigger level-complete (win-check is overlay-internal); resident death-state handlers (`FUNC_8005B134` states 8/9/10 → `0x8005c110/258/cce8`) write **no** transition machinery (death/respawn is within-level; game-over→shell is also overlay-initiated).

⇒ **Native trigger localized + lever captured:** per-scene overlay verb (dispatcher `0x80054964` → `0x800bxxxx`) detects level-exit → calls a resident transition-initiator (`0x800496d8/a8b4/b3c0`, sets `[0x800823a0]` type + fade + destination) → fade handler → shell SM → orchestrator [[FUNC_8005222C]] (substate 5) → scene-init → spawn ([[Experiment - Warp landing diversion]]). The CAPTURED lever is `[0x800823a0]=6`; the un-captured residual is the overlay exit-setup that picks the real destination (GAP-0033).

## Pass-3 (2026-06-21) — overlay verb DECODED + two model corrections (GAP-0033 advance)
Static (jal/store-EA scan over EXE **+ all Region-A overlays**, `tools/exe_read.py`) plus a targeted runtime confirmation (LOCAL-ONLY, GAP-0001).

**Correction A — the "initiators" `0x800496d8/a8b4/b3c0` are `sh [0x800823a0]` STORE-PCs, not functions.** `--store-ea 0x800823a0` = 16 writers; the three type stores sit inside enclosing functions:

| type | store-PC | enclosing fn | callers |
|--:|---|---|---|
| 1 | `0x800496d8` | **`0x80048138`** | 1 EXE (`0x8004efd8`) |
| 2 | `0x8004a8b4` | **`0x8004a700`** ([[FUNC_8004A700]]) | 6 EXE + **2 OVERLAY** |
| 6 | `0x8004b3c0` | **`0x8004abf4`** ([[FUNC_8004ABF4]]) | 1 EXE (`0x8004f0e8`, the gameplay gate) |

A `jal`-scan of every overlay + the EXE finds **no direct call to the store-PCs** (they are mid-function) — which is why the prior "overlay verbs call the initiators" was only inferable.

**Q1 ANSWERED — the inference is now PROVEN.** `0x8004a700` (type-2) **is `jal`'d from overlay verbs**: **`0x800b3e94`** in **LEVEL06\LEVEL.BIN** (= the scene-3 table verb `0x800b3e88`+0xc) and **`0x800b4ae0`** in LEVEL04\LEVEL1.BIN. Decode of the scene-3 verb `0x800b3e88` (an **interior case-label** of the overlay's main handler — starts `addiu a2,sp,16`, not a prologue): it calls **`FUNC_8004A700(a2=&sp16, a3=3)`** then sets `[0x800823a0]=2` + fade `[0x80082470]=60`. **`a3` is a destination/mode arg** (LEVEL06=3, LEVEL04=0); `0x8004a700` branches on it (`bne s4,zero,…`) and in the a3≠0 path manages the exit counter `[0x800a6594]`. ⇒ the **type-2 overlay path carries an explicit destination (a3)**.

**Correction B (RUNTIME, LOCAL-ONLY) — the type-6 path is a PER-TICK updater, not a one-shot; the gate fields are NOT the exit trigger.** The native gate `0x8004f0e8` calls `0x8004abf4` iff `[0x800a657c]==0 && [0x800a6594]≥0`. In normal play (`level02.sav`, scene 3) those read `0, 4` ⇒ **gate OPEN, `0x8004abf4` invoked EVERY tick with no transition** (execTrace: fires each gameplay frame). So `[0x800a657c]/[0x800a6594]` are a *"transitions-allowed"* precondition. `0x8004abf4` operates on actor ptr **`[0x80090748]`** (`beq s1,zero` early-exit) — runtime: that ptr is **NULL** mid-level ⇒ it early-exits, so the type-6 **commit countdown `[0x8008223c]` (0→5, commit at 5, inc `0x8004b3a8`; gated by `[0x8009b889]&0x20==0 && scene_id!=16`) stays dormant** (`[0x8008223c]` rests 0, zero writers in 3 frames; forcing it to 4 did nothing). → [[FUNC_8004ABF4]].

**Q4/Q5/Q6 — destination is shell-resolved; type-6 carries none.** `0x8004abf4` writes only `[0x80082444]`,`[0x800823a0]=6`,`[0x80082470]=30` — **no destination**. The shell SM resolves it at **`0x8004fda0`**: `dest = scene_table[ [0x8008245c] ]` (`scene_table @0x80077fa0`), **UNLESS `[0x8008225c]!=0` → force dest=16** (`0x8004fde4`). `scene_table[16]=0xffffffff`; **scene 16 only ever comes from the force-flag** (the map/results screen). `[0x8008245c]` (index) is written by **7 sites, ALL in the shell SM** — never by gameplay/overlay. ⇒ forcing `[0x800823a0]=6` mid-gameplay skips the shell-phase index selection + orchestrator resource load; the shell reads stale `idx`/force-flag → scene 16 with no prepared resources → scene-init(16) crash. **The missing setup = the shell-phase destination index + orchestrator resource sequencing, which a gameplay-side lever poke cannot supply.**

**Q7/Q8 — a clean level→level was NOT achieved this pass and is not lever-reachable.** The native trigger is a chain, not one variable: live exit-actor `[0x80090748]` → per-tick `0x8004abf4` countdown `[0x8008223c]`→5 → type-6 arm → fade → **shell** destination-select + orchestrator resource-load → scene-init+spawn. The only path that carries a destination from gameplay is the **type-2 overlay** call `FUNC_8004A700(a3=dest)` — scriptable but overlay/scene-specific. GAP-0035 clean in-game level→level **stays blocked on the shell-phase destination/resource setup** (= this GAP-0033 residual).

## Architecture (static `exe_read.py` + dynamic confirmation)
**Per-frame top loop** (region `0x8004fe70`): a gate selects dispatch —
```
v0 = [0x8008224e]                 ; GATE (halfword)
bne v0, zero, 0x8004fedc          ; gate != 0 -> shell/menu
jal 0x8004ecd4                    ; gate == 0 -> GAMEPLAY loop
...
0x8004fedc: jal 0x8004f478        ; SHELL/menu handler (own sub-state machine)
```
- **Gameplay loop `0x8004ecd4`** (`0x8004f020`): `jal 0x80054c90` (checkpoint-save) → reads `scene_id` → `jal 0x80054964(scene_id)` (the GAP-0033 dispatcher) → more.
- **Shell SM `0x8004fa40`** dispatches by substate `[0x8008243c]`: `jr [0x8001b3c4 + sub*4]` (8 handlers). Substate **0** sets scene-table index `[0x8008245c]=1`; **1→11, 2→2, 3→7, 4→12**; **substate 5 = load case `0x8004fca0`** → `jal 0x8005222c` (orchestrator). Common tail commits **`scene_id = scene_table[ [0x8008245c] ]`** (`scene_table @ 0x80077fa0 = {0x11,1,3,2,6,0xa,0xb,4,5,0xe,7,0xc,0xd,9,8,0xf,…}`).

## Findings

### 1. Orchestrator FUNC_8005222C is shell-only; cold boot does NOT use it (CONFIRMED, runtime)
`execTrace` at `0x8005222c` across the cold-boot movie → **0 hits** (only scene-init `0x8005b70c` @ f3486 a0=1, spawn `0x80046b20` @ f4518 a1=1); no `scene_id=19→0→restore` writes. The cold boot reaches LEVEL01 via the **substate-0 path** (`[0x8008245c]=1` → `scene_id=scene_table[1]=1` → scene-init). ⇒ the orchestrator is the **in-game / level→level** transition wrapper (reload globals + fade for an already-running game), reached only from the shell SM (substate-5 caller `0x8004fca8`, a0=1; or 2nd caller `0x8005028c`, a0=0, gated on state byte `0x8009b888` bit0). → [[FUNC_8005222C]].

### 2. Gameplay vs shell — confirmed dynamically
From `level02.sav` (scene 3, in-level), 3-frame `execTrace`: **gameplay loop `0x8004ecd4` ×2 + dispatcher `0x80054964` ×2; shell SM `0x8004fa40` = 0 hits.** Gate `[0x8008224e]=0` during gameplay with **no writers** in 3 frames. So the shell substate machine (incl. substate-5/orchestrator) is dormant during play.

### 3. Why mid-gameplay scene_id pokes crash (CONFIRMED — `tools/trace_shell_warp.py crash`)
`scene_id [0x80082504]` is **READ ~15×/frame** during gameplay (15 distinct PCs in one frame: dispatcher path `0x8004f038`, plus `0x8004exxx`, `0x80053xxx`, `0x80056xxx`, `0x80051xxx`, and **overlay** `0x800b4840/0x800b48b0`). Isolation:
| forced write (mid-gameplay, level02.sav) | result |
|---|---|
| `scene_id` 3→6 | **CRASH** at `0xbfc02bac` (frame +1) |
| substate `[0x8008243c]`=5 alone | **no crash** (shell SM not the active dispatch) |
| gate `[0x8008224e]`=1 alone | **no crash** (pc `0x00001a74`; enters shell handler) |
⇒ the crash is caused by **mutating `scene_id` during active gameplay** (every consumer then dispatches the wrong scene against the loaded level's data), **not** by substate. This explains the documented [[Finding - Level-warp mechanism]] `0xbfc0d8e0`-class crash: the old "clean lever" (`substate=5 + scene_id=target`) crashed because of its `scene_id` half. **Violated precondition: `scene_id` is immutable during gameplay; only the shell phase (gameplay loop not running) may change it.**

### 4. The gameplay↔shell gate `[0x8008224e]` (CONFIRMED) — the native handoff lever
`--store-ea 0x8008224e` → **6 writers**: only **`0x8004f3ac` sets it non-zero** (enter shell — after the finalizer `0x80045a60` + `0x80043500`, when a shell sub-state hits 128); the other 5 set it 0 (→gameplay), incl. **scene-init `0x8005b898`** at load-complete (the shell→gameplay handoff). The non-zero writer lives in the shell/menu handler, so the **gameplay→shell handoff is shell-internal, gated by a level-exit condition** the gameplay dispatcher must raise.

## The full native chain (Pass-1 bound + Pass-2 capture)
per-scene **overlay verb** (`0x80054964` → `0x800bxxxx`) detects level-exit → **calls a resident transition-initiator** (`0x800496d8/a8b4/b3c0`) that sets the **transition-state lever `[0x800823a0]`** (+fade color +helpers) → **fade handler** (`0x8004f230`-region) progresses the fade + tears down the level (`[0x800822f8]→0`) → gate `[0x8008224e]` flips non-zero at `0x8004f3ac` → shell/menu handler `0x8004f478` → shell SM substate machine → **substate 5 → orchestrator [[FUNC_8005222C]]** + target load `0x8003cf2c(scene_id)` → **scene-init `0x8005b714` → spawn `0x80046b20`** (the proven landing). **Pass-2 CAPTURED the lever** (`[0x800823a0]=6` → scene-init, above). The **safe pre-latch destination** is `[0x8008245c]`/`scene_table` (shell phase) — but its selection for an *in-game* exit is done by the overlay (defaults to invalid scene 16 when forced).

**Residual (un-captured):** the overlay verb's exact level-exit *condition* + its destination/resource setup (so a forced transition lands in a real next level instead of scene 16) — **GAP-0033** (dispatcher `0x80054964` per-scene verbs).

## Confidence
- Orchestrator shell-only; not cold boot (substate-0 path) — **CONFIRMED (execTrace)**.
- Gameplay loop `0x8004ecd4` + dispatcher `0x80054964` run in-level; shell SM dormant — **CONFIRMED**.
- `scene_id` immutable in gameplay (read ~15×/frame); mutation → crash `0xbfc02bac`; substate=5 / gate=1 alone safe — **CONFIRMED (reproduced)**.
- Gate `[0x8008224e]` (gameplay 0 / shell !=0) + 6 writers; handoff shell-internal — **CONFIRMED (static + runtime)**.
- **Native trigger LEVER = transition-state `[0x800823a0]` (resident initiators types 1/2/6 ← overlay verbs); type-6 reproducibly initiates gameplay→shell-SM→scene-init** — **CONFIRMED (reproduced 2× + type scan)**.
- The overlay level-exit *condition* + clean destination selection — **INVESTIGATING / bounded to GAP-0033** (the lever is captured; the overlay exit-setup is not).

## Related
[[Experiment - Warp landing diversion]] · [[Experiment - Initial spawn write-watch]] · [[FUNC_8005222C]] · [[FUNC_8005B714]] · [[FUNC_80046B20]] · [[Gameplay - Warp and Level Transition]] · [[Gameplay - Events and Triggers]] · [[Finding - Level-warp mechanism]] · [[MEM - Event System Globals]] · `tools/trace_shell_warp.py` · `tools/exe_read.py`
