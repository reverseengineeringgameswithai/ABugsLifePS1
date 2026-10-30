---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Functions/FUNC_8005222C.md
aliases: []
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Functions/FUNC_8005222C.md`
- Replacement/current location: `ObsidianVault/Canon/Functions/FUNC_8005222C_level-transition_orchestrator.md`
- Archive reason: Existing function note; migrate only evidence-backed claims and link C source where available.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: FUNC_8005222C — level-transition orchestrator
type: function
address: 0x8005222C
confidence: CONFIRMED (orchestrator role); some inner steps LIKELY
tags: [function, warp, transition, loader, milestone6, gap-0035]
---
# FUNC_8005222C — level-transition orchestrator

> The transition wrapper the shell state machine runs to change level/scene. **It saves the requested `current_scene_id`, swaps it to the "loading" scene 19 to load global/common resources, runs a screen-fade + per-step resource pass, resets the gameplay-state cluster + scroll/subsystem state, then restores `current_scene_id` to the target.** It does **not** load the target stage's files itself (that is a separate `0x8003cf2c(scene_id)` call from the shell SM) and does **not** move the player. STATIC (`exe_read.py --disasm`); live execution unproven ([[Finding - Level-warp mechanism]] / GAP-0001).

| Field | Value |
|---|---|
| Bounds | `0x8005222c … 0x800524b8` (163 instrs, `jr ra` @ `0x800524b0`) |
| Role | level/scene transition **orchestrator** (load-global + fade + reset wrapper) |
| Callers | `0x8004fca8`, `0x8005028c` — both in shell SM [[FUNC_8005B714|main_shell_state_machine 0x8004fa40]] (reached via substate `[0x8008243c]=5` → load case `0x8004fca0`, [[Finding - Level-warp mechanism]]) |
| Arg | `a0` (→ `s5`) = **mode selector** (gates branches: `s5==0` vs `≠0` → different fade/step counts 390 vs 210) |
| Returns | status `v0 = (s1≥18) ? 4 : 0` (load-completed flag) |

## Decoded sequence
1. **Save target:** `s8 = [0x80082504]` (the requested scene/stage), read at entry.
2. **Swap to loading scene + load globals:** `[0x80082504] = 19`; `[0x800823ac]=3134`; `jal 0x80039478`; **`jal 0x8003cf2c(a0=19)`** → loads **global/common resource id 19** ([[FUNC_8003CF2C]]); `jal 0x80046ac0(21)`.
3. **Resource-select + screen-fade loop** (`s1 = 1..16`, ≤17): per step `jal 0x8003a314` (resource selector, ≈[[FUNC_8003A318]]) + screen-fade `jal 0x80054aac(r,g,b,2)` / `0x80054ad4` (RGB `128,128,128`→`0,0,0`, progress bounded `|s0|<68`); inner `jal 0x8003f2f0 ×40` (clears 40 slots).
4. **Scroll reset + scene_id clear:** `jal 0x8003df14(0,-8)` ([[FUNC_8003DF14]], scroll/offset reset); `[0x80082504] = 0`; clear state halfwords `0x80082388 / 0x80082494 / 0x80082430`.
5. **Finalize:** `jal 0x80045a60()` ([[FUNC_80045A60]], transition finalizer — clears flag `0x80082478` + subsystem reset).
6. **Restore target:** `[0x80082504] = s8`; return status.

## Globals read / written
- **Writes `current_scene_id 0x80082504` three times** — `=19` (loading), `=0` (clear), `=s8` (restore target).
- Writes state-cluster `0x800823ac`, and halfwords `0x80082388 / 0x80082494 / 0x80082430` (=0). Reads `0x80082492` (lh, a screen/fade flag).
- **Does NOT write player position** `0x800a6500/04/08` (verified `--store-ea`). No camera writes.

## Answers (GAP-0035)
- **Reloads resources:** YES — global id 19 via `0x8003cf2c`, + `0x8003a314` selector, + `0x80046ac0(21)`. (The *target* stage's files load separately via `0x8003cf2c(scene_id)` from shell-SM caller `0x800503cc`.)
- **Reseeds gameplay state:** YES — clears the `0x80082xxx` state halfwords here; the cursor reseed + cluster zero is [[FUNC_8005B714]] on scene-init.
- **Changes scene-handler selection:** YES (indirectly) — it drives `current_scene_id`, which the per-tick dispatcher uses (`jr [0x8001b4fc + (scene_id−1)·4]`).
- **Moves player:** NO (not in this path → player placement is a separate level-data/spawn step — open).
- **Plus:** screen fade, scroll-offset reset, subsystem/audio finalize.

## Runtime findings (2026-06-21) — shell-only; NOT cold boot → [[Experiment - In-game warp trigger]]
- **The orchestrator does NOT run during the cold LEVEL01 boot.** An `execTrace` at `0x8005222c` across the boot movie got **0 hits** (only scene-init `0x8005b70c` @ f3486 + spawn `0x80046b20` @ f4518), and no `scene_id=19→0→restore` writes appear. **The cold boot uses the substate-0 path** instead: shell-SM substate 0 sets scene-table index `[0x8008245c]=1` → common tail commits `scene_id = scene_table[1] = 1` → scene-init spawns. ⇒ this orchestrator is the **in-game / level→level transition** load wrapper (reload globals + fade for an *already-running* game), not the first-level entry.
- **Both callers are shell-phase only** (region `0x8004fxxx`): `0x8004fca8` = the substate-5 load case (`a0=1`); `0x8005028c` = a 2nd shell branch (`a0=0`) **gated on state byte `0x8009b888` bit0** (sets the bit + `[gp+0x4c4]=1` before the call). So the `a0` mode selector distinguishes the substate-5 path (1) from the bit-gated path (0).
- **Reachable only in shell mode.** The per-frame top loop (`0x8004fe70`) chooses by gate **`[0x8008224e]`**: `==0` → gameplay loop `0x8004ecd4`; `!=0` → shell/menu `0x8004f478` (whose sub-state machine reaches substate 5 → this orchestrator). During gameplay the gate is **0** with no writers, so the orchestrator is never reached mid-play ⇒ a native in-game warp first needs the gameplay→shell handoff (gate `!=0`).
- **Reached via the transition-state lever (2026-06-21, max effort).** The native gameplay→shell handoff is initiated by the **transition-state var `[0x800823a0]`** (resident initiators `0x800496d8/a8b4/b3c0`, called by the per-scene overlay verbs on level-exit). Poking `[0x800823a0]=6` from gameplay reproducibly drives the chain into scene-init `FUNC_8005B714`; the fade handler tears down the level before the gate flips and this orchestrator runs. So this orchestrator sits **downstream** of `[0x800823a0]` in the native chain — confirming it is not the trigger, only the shell-side load wrapper. → [[Experiment - In-game warp trigger]].

## Confidence
- Orchestrator role + the scene_id 19→0→target sequence + callers — **CONFIRMED (decoded)**.
- Orchestrator is shell-only and does NOT run in cold boot (cold = substate-0 path) — **CONFIRMED (runtime execTrace)**.
- 2nd caller `0x8005028c` gated on `0x8009b888` bit0; `a0` = mode selector (1=substate-5, 0=bit-gated) — **CONFIRMED (decoded)**.
- The 17-step loop = resource-select + fade — **LIKELY** (fade calls confirmed; per-step resource semantics summarized).
- No player placement here — **CONFIRMED**.

## Remaining unknowns
- The **level-exit event** that natively flips the gameplay→shell gate `[0x8008224e]` (so the shell SM can reach substate 5) — GAP-0033-gated (the gameplay dispatcher `0x80054964` / a level-complete/death condition); not captured.
- `0x8003a314` is **1 instr before** the documented [[FUNC_8003A318]] entry (`0x8003a318`) — alternate entry vs symbol off-by-one (note, not promote).
- Where the **target stage** load (`0x8003cf2c(scene_id)` @ `0x800503cc`) sits in the shell-SM sequence relative to this orchestrator.

## Related
[[Gameplay - Warp and Level Transition]] · [[Experiment - In-game warp trigger]] · [[Finding - Level-warp mechanism]] · [[FUNC_8003DF14]] · [[FUNC_80045A60]] · [[FUNC_8003CF2C]] · [[FUNC_8003A318]] · [[FUNC_8005B714]] · [[FUNC_80046B20]] · [[MEM - Event System Globals]] · `tools/exe_read.py` · `tools/trace_shell_warp.py`
