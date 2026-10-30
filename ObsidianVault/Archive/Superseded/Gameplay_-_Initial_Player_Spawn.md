---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Gameplay - Initial Player Spawn.md
aliases:
  - "Gameplay - Initial Player Spawn"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Gameplay - Initial Player Spawn.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Gameplay_-_Initial_Player_Spawn.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Gameplay - Initial Player Spawn
type: core
updated: 2026-06-20
status: CONFIRMED (runtime)
tags: [core, gameplay, player, spawn, warp, milestone6, gap-0035, runtime]
---

# Gameplay — initial level-load spawn (GAP-0035 layer 1)

> The layer-1 writer that sets the player's live position at level load (before checkpoint-save / respawn-restore — [[Gameplay - Player Spawn and Placement]]). **RESOLVED 2026-06-20 by the single runtime write-watch ([[Experiment - Initial spawn write-watch]]): the writer is [[FUNC_80046B20]]`(a0=player 0x800a6500, a1=scene_index)`, called from scene-init [[FUNC_8005B714]]; the source is a RESIDENT EXE table at `0x80077314 + index*12` (12-byte X/Z/heading records) — NOT a LEVEL.DAT placement record and NOT the LEVEL.BIN-baked area at `0x80096d18`. Both prior hypotheses are overturned.** The earlier static analysis (9 approaches, below) correctly proved the write is **register-indirect** (`a0` pointer) and un-pinnable statically — exactly because the store hides behind the `a0` arg and the first physical write is a BIOS `memset`. The write-watch is local-only ([[DuckStation Fork Reproducibility]] / GAP-0001).

## Runtime result (CONFIRMED — [[Experiment - Initial spawn write-watch]], emulator frame 4518, scene_id=1)
**[[FUNC_80046B20]]`(a0 = 0x800a6500, a1 = 1)`** (entry `0x80046b20`; runtime `a0/a1` captured by `execTrace`):
1. Saves lives `+0xa0`, then **memsets the 168-byte (0xA8) block to 0** (helper `0x8005f7ac` → BIOS `memset` `0xbfc02bb4` — the byte-writer a naive `findFirstWrite` reports).
2. Reads source record `s0 = 0x80077314 + a1*12` (runtime `s0=0x80077320`) and writes:
   - `+0x00` **X** ← record word0 (`0x301f4` = 197108); `+0x08` **Z** ← record word1 (`0x7855f` = 492895)
   - `+0x04` **Y** = `FUNC_80037A38(pos) − 0x100` (ground/floor height — **computed, not stored**)
   - `+0x20/+0x28/+0x78` **heading** ← record word2 (`0xdb1` = 3505)
   - `+0x10/14/18` previous/**render copy** ← live XYZ; `+0x50/54/58` **respawn anchor** ← live XYZ
   - flags/counters `+0x94=4`, `+0x98=0x11`, `+0x4c=0x80000000`; **lives `+0xa0` restored**
3. Source table `0x80077314` is **resident in the boot EXE** (`SCUS_942.88` file offset `0x67b14`; byte-exact RAM↔EXE cross-check). Record **1 = LEVEL01**; records 0–17 = plausible per-scene coordinate triples ⇒ **the editable player-start lever** (edit `0x67b14 + index*12`).
4. Called from `0x8005baa4` inside scene-init [[FUNC_8005B714]]`(scene_id)` (`a1 = s2 = a0 = scene_id`), alongside the `0x80082xxx` state-cluster zeroing ⇒ `index = scene_id` (LIKELY; ==1 here). **Warp landings re-enter scene-init ⇒ same fn/table, indexed by target scene_id** (LIKELY-HIGH; live-warp *exec* still blocked).

## Pre-runtime static characterization (still valid; explains why static alone couldn't pin it)
- **The player block is a pointer-arg-passed struct.** The integrator [[FUNC_8003633C]] takes the block as `a0 → s7` (`0x80036344`) and writes pos via `sw _,0/4/8(s7)`. So functions receive `&player` as an argument; there is **no global pointer-to-player** variable (`0x800a6500`/`0x800a6510`/`0x800a6550` appear as data words **0** times). *(Runtime-confirmed: the spawn writer [[FUNC_80046B20]] also takes `a0=&player`.)*
- **Player struct layout** (base `0x800a6500`): live XYZ `+0/+4/+8`, previous/render copy `+0x10/+0x14/+0x18`, respawn anchor `+0x50/+0x54/+0x58`. All **boot to 0** (BSS, beyond the loadable image) — so a load-time write MUST establish the start position.
- **The block has 0 absolute and 0 gp-relative writers.** Its only constant-base writers are the **respawn-restore** [[FUNC_8005B134]] tail and the **checkpoint-save** [[FUNC_80054C90]] — both of which *copy within* the block (anchor↔live), neither seeds it from level data.

## Why static can't pin the initial writer (9 exhausted approaches)
| # | Approach | Result |
|--:|---|---|
| 1 | `--store-ea` constant-base writers of live `0x800a6500/04/08` | only [[FUNC_8005B134]] (respawn) |
| 2 | `--store-ea` of anchor `0x800a6550/54/58` | only [[FUNC_80054C90]] (checkpoint) |
| 3 | absolute `--xref` writers of `0x800a6500` | **0 writers** (39 readers) |
| 4 | gp-relative writers (gp-off `0x4768`) | 0 |
| 5 | 21 `&player` pointer-materialize sites → offset writes | none write XYZ/anchor; `&player` is **passed as `a0`** to callees |
| 6 | callees receiving `&player` (`0x80045678`/`0x80044d28`/`0x8005044c`) | query / effect / bookkeeping — not spawn |
| 7 | DAT parser [[FUNC_8001CDC0]] | builds record tables; **does not write the player block** |
| 8 | "set-vec3 via `a0`" functions in the load path | 1 hit `0x8004dd98` = a per-frame **interpolator** (false positive) |
| 9 | overlay init `level_overlay_init 0x800b39a4` | stages overlay-baked records `0x800b3f54 → 0x80096d18` (object tables) — **no player write** |

⇒ the load-time writer obtains `&player` through `a0` and the first physical write is a BIOS `memset`, so constant-base/`jal`-target scanning can't follow it. **The runtime watch was the only resolution** — and it found exactly this shape ([[FUNC_80046B20]], `a0`-passed, memset-masked).

## Source — RESOLVED (runtime; both prior hypotheses overturned)
The spawn coords are **NOT level data**: they are a **resident table baked in the boot EXE** at `0x80077314 + scene_index*12` (`SCUS_942.88` file offset `0x67b14`; byte-exact RAM↔EXE). 12-byte records: **word0→X, word1→Z, word2→heading**; **Y is computed** (`FUNC_80037A38(pos) − 0x100`, ground height). Record 1 = LEVEL01 (X `0x301f4`, Z `0x7855f`, heading `0xdb1`).
- ~~LEVEL.DAT placement record~~ **REFUTED** — the source ptr `s0=0x80077320` is in the resident EXE, not `[DATbase 0x80082498, …)`; the DAT parser [[FUNC_8001CDC0]] does not feed it.
- ~~LEVEL.BIN-baked records at `0x80096d18`~~ **REFUTED** — source is `0x80077314`, not the `0x80096d18` region.

## Relationship to the rest of the model
Initial spawn (layer 1, **[[FUNC_80046B20]]**) → [[FUNC_80054C90]] checkpoint-save (layer 2) → [[FUNC_8005B134]] respawn-restore (layer 3). **CORRECTION:** the spawn IS invoked by scene-init [[FUNC_8005B714]] (at `0x8005baa4`, `a1=scene_id`) — previously believed to "write no player position." So **scene-init = `0x80082xxx` state-cluster zero + noise-cursor seed + player spawn**. It remains independent of the warp *orchestrator* [[FUNC_8005222C]] (resources/scene/fade), which writes no player pos. Load order: orchestrator/loaders run → level data resident → **scene-init spawns the player from `table[scene_id]`** → first gameplay frame ([[FUNC_8003633C]] integrator takes over) → checkpoint-save can snapshot.

## Confidence
- Writer = [[FUNC_80046B20]]`(a0=player, a1=scene_index)`; field offsets — **CONFIRMED (runtime: write-watch + execTrace, reproduced 2×; disasm)**.
- Source = resident EXE table `0x80077314 + index*12` (word0→X, word1→Z, word2→heading; Y computed) — **CONFIRMED (ptr capture + value-match + EXE cross-check)**.
- Caller = scene-init [[FUNC_8005B714]] @ `0x8005baa4`; `index == scene_id` (= level-select value; `==stage`) — **CONFIRMED** (live diversion to scene 3/6/2/4 → spawn `a1` followed; [[Experiment - Warp landing diversion]]).
- Table is per-scene (records 1–17 = levels) — **CONFIRMED** (indices 1,2,3,4,6 byte-proven live + 7-level save-anchor survey).
- Pre-runtime: player block = pointer-arg struct, register-indirect, static-unresolvable — **CONFIRMED (9 approaches; now explained)**.

## Next proof step — DONE (both halves)
~~One runtime write-watch on `0x800a6500` across a LEVEL01 cold boot.~~ **Executed 2026-06-20 → [[Experiment - Initial spawn write-watch]]** (`tools/trace_initial_spawn.py`). **Warp landing also executed 2026-06-21 → [[Experiment - Warp landing diversion]]** (`tools/trace_warp_landing.py`): non-LEVEL01 landings (scene 3/6/2/4) reuse the same fn/table, `index==scene_id`, clean (no crash). The cold initial spawn and a warp landing are **one code path**. Residual: an **in-game (mid-level)** orchestrator warp ([[FUNC_8005222C]]) still crashes from mid-gameplay (the *trigger* path, not the landing).

## Modding relevance
The **editable player-start** lever is **`SCUS_942.88` file offset `0x67b14 + scene_index*12`** (X=word0, Z=word1, heading=word2) — a resident EXE edit, NOT a LEVEL.DAT edit. Y auto-snaps to ground (`FUNC_80037A38 − 0x100`), so only X/Z/heading need setting. Runtime: poke `0x80077314 + index*12` (or the live block / respawn anchor `0x800a6550/54/58`) to relocate.

## Related
[[Experiment - Initial spawn write-watch]] · [[Experiment - Warp landing diversion]] · [[FUNC_80046B20]] · [[FUNC_8005B714]] · [[Gameplay - Player Spawn and Placement]] · [[Gameplay - Warp and Level Transition]] · [[FUNC_8005B134]] · [[FUNC_80054C90]] · [[FUNC_8003633C]] · [[FUNC_8001CDC0]] · [[FUNC_8005222C]] · [[MEM - Player state 800A6500]] · [[DuckStation Fork Reproducibility]] · `tools/trace_initial_spawn.py` · `tools/trace_warp_landing.py` · `tools/exe_read.py`
