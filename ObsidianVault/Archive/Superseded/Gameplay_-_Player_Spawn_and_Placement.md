---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Gameplay - Player Spawn and Placement.md
aliases:
  - "Gameplay - Player Spawn and Placement"
migration_action: split
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Gameplay - Player Spawn and Placement.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Gameplay_-_Player_Spawn_and_Placement.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Gameplay - Player Spawn and Placement
type: core
updated: 2026-06-20
tags: [core, gameplay, player, spawn, checkpoint, warp, milestone6, gap-0035]
---

# Gameplay — Player spawn & placement (GAP-0035)

> Answers *which function places the player after level load / scene transition, and from what source* ([[Gameplay - Warp and Level Transition]]). **Conclusion: player placement is a 3-layer checkpoint/respawn system, NOT part of the warp orchestrator. (1) the initial level-load spawn [[FUNC_80046B20]]`(player, scene_index)` writes the live position from a resident EXE table `0x80077314 + index*12` (runtime-CONFIRMED 2026-06-20), (2) a distance-gated checkpoint-save `0x80054c90` snapshots live→anchor during play, (3) the respawn handler `FUNC_8005B134`'s tail restores anchor→live on death/respawn with a full player-state reset.** Layers 2/3 STATIC (`exe_read.py`); layer 1 byte-proven by runtime write-watch → [[Experiment - Initial spawn write-watch]].

## Player-position memory (CONFIRMED)
| Addr | Field | Role |
|---|---|---|
| `0x800a6500/04/08` | **live** player X/Y/Z | the active position; Y per-frame = collision integrator [[FUNC_8003633C]] (via reg-ptr `s7`) |
| `0x800a6510/14/18` | **previous/render** X/Y/Z | second copy written alongside live on respawn; read by integrator `0x80036d5c` |
| `0x800a6550/54/58` | **respawn anchor** X/Y/Z | the saved checkpoint position (source for respawn) |
| `0x800a6590` | state flags (hword) | checkpoint-save sets bit3 (`| 0x8`) |

## The three placement layers
**Layer 1 — initial level-load spawn → [[Gameplay - Initial Player Spawn]] (RESOLVED, runtime 2026-06-20).** The live position `0x800a6500/04/08` (BSS-zero at boot) is set at level load by **[[FUNC_80046B20]]`(a0=player, a1=scene_index)`**, called from scene-init [[FUNC_8005B714]]. It memsets the 168-byte block (BIOS `memset` via `0x8005f7ac` — preserving lives `+0xa0`), then fills it from a **resident EXE table `0x80077314 + index*12`**: word0→X, word1→Z, word2→heading; **Y is computed** (`FUNC_80037A38(pos) − 0x100`, ground height). It also writes the render copy `+0x10/14/18` and **respawn anchor `+0x50/54/58`** from the live XYZ. Record 1 = LEVEL01 (X `0x301f4`, Z `0x7855f`). The prior static prediction (register-indirect `a0` write, 9 approaches exhausted) is confirmed as the *reason* it was static-invisible; the source hypotheses (LEVEL.DAT / LEVEL.BIN-baked `0x80096d18`) are both **REFUTED** — the source is resident in the boot EXE (`SCUS_942.88` offset `0x67b14`).

**Layer 2 — checkpoint-save `0x80054c90`** (called per frame from the gameplay loop `fcn.8004ecd4` @ `0x8004f020`). Iterates the **64×0x84** object array (the seed/checkpoint records, base ~`0x800a0014`), and when a **distance test** passes (`slt` gate @ `0x80054e20`) copies the **live** position into the **anchor**:
`[0x800a6550/54/58] = [0x800a6500/04/08]` (writers `0x80054e70/e78/e80`), `[0x800a6578]=…`, `[0x800a6590] |= 8`. ⇒ "when the player is near a checkpoint trigger, save the current position as the respawn anchor."

**Layer 3 — respawn restore `FUNC_8005B134` common tail** (`0x8005b1bc..0x8005b2dc`, runs after the state-case dispatch). Reads the **anchor** and writes it to the **live** position **and** the previous/render copy, then **zeroes a large block of player state** (velocity / flags / counters `0x800a651c..0x800a65xx`):
```
a2,v1,a3 = [0x800a6550/54/58]                  ; read anchor
[0x800a6500/04/08] = a2,v1,a3                  ; live pos      (writers 0x8005b29c/2a4/2ac)
[0x800a6510/14/18] = a2,v1,a3                  ; previous/render copy (0x8005b2b4/2bc/2c4)
[0x800a651c..0x800a6534] = 0 ; velocity/flags  ; full reset
```
[[FUNC_8005B134]] is reached via a jalr/state table and only runs in specific states (`v0∈[3,10]` — death/respawn/transition), which is why an 8-idle-frame live trace saw **0** player-Y writes here.

## Answers (GAP-0035 placement)
1. **Writer after transition/respawn:** [[FUNC_8005B134]] common tail (respawn) + initial-load spawn [[FUNC_80046B20]] (layer 1). Per-frame movement = [[FUNC_8003633C]] (excluded — integrator, not placement).
2. **Source of spawn coords:** the live position's *first* value (level-load) is the **resident EXE table `0x80077314 + scene_index*12`** (word0→X, word1→Z, word2→heading; Y computed) — runtime-CONFIRMED, **not** LEVEL.DAT. The **respawn anchor `0x800a6550/54/58`** is seeded from that same spawn, then later overwritten by checkpoint-save `0x80054c90` from the live position.
3. **Downstream of?** Placement is **NOT** downstream of the warp orchestrator [[FUNC_8005222C]] (no player writes there), nor of [[FUNC_8005B714]] (that zeroes the `0x80082xxx` cluster, not the player block). Respawn = a separate state-handler; checkpoint-save = the gameplay loop; load-spawn = the loader path.
4. **Writes XYZ only, or more?** **More:** live XYZ + previous/render copy + a full **velocity/flags/counter reset** (layer 3) and a checkpoint **flag bit** (layer 2). **No camera writes observed** in these paths (camera is a separate system); no explicit heading/velocity *set* (velocity is zeroed).
5. **Connection to transition:** the warp does resources+scene+fade ([[FUNC_8005222C]]) and gameplay-state reset ([[FUNC_8005B714]]); **player placement is independent** — the loaded level data spawns the player, and the checkpoint/respawn pair maintains the anchor thereafter.

## Confidence
- Checkpoint-save `0x80054c90` (live→anchor, distance-gated) — **CONFIRMED (decoded)**.
- Respawn tail [[FUNC_8005B134]] (anchor→live + reset) — **CONFIRMED (decoded)**.
- Anchor `0x800a6550/54/58` = respawn source — **CONFIRMED**.
- Initial level-load spawn = [[FUNC_80046B20]]; source = resident EXE table `0x80077314 + index*12` — **CONFIRMED (runtime, [[Experiment - Initial spawn write-watch]])**.
- "0x80054c90 = checkpoint vs seed-proximity" exact trigger — **LIKELY** (64×0x84 array = the seed/checkpoint records; distance-gated save).

## Modding relevance
A level editor's **player start** is the resident EXE table record — **`SCUS_942.88` file offset `0x67b14 + scene_index*12`** (X=word0, Z=word1, heading=word2; Y auto-snaps to ground). The **checkpoint** behavior (auto-save near triggers) is `0x80054c90`; the **respawn snap** is [[FUNC_8005B134]]. Editing the anchor `0x800a6550/54/58` at runtime relocates the respawn point; the persistent start is the EXE-table edit (not a LEVEL.DAT field).

## Remaining unknowns / next step
- ~~Pin the layer-1 load spawn writer + source field.~~ **DONE (runtime 2026-06-20)** → [[FUNC_80046B20]] + resident EXE table `0x80077314` ([[Experiment - Initial spawn write-watch]]). Residual: confirm `index==scene_id` (vs stage) on a non-LEVEL01 entry; capture a live **warp landing** (same fn/table expected; blocked on shell-phase fixture).
- The exact checkpoint trigger condition in `0x80054c90` (which object/record arms the save).

## Related
[[Gameplay - Initial Player Spawn]] · [[Experiment - Initial spawn write-watch]] · [[FUNC_80046B20]] · [[Gameplay - Warp and Level Transition]] · [[FUNC_8005B134]] · [[FUNC_80054C90]] · [[FUNC_8003633C]] · [[FUNC_8005B714]] · [[FUNC_8005222C]] · [[MEM - Player state 800A6500]] · [[Gameplay - DAT Event Stream]] · `tools/trace_initial_spawn.py` · `tools/exe_read.py`
