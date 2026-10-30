---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Functions/FUNC_80046B20.md
aliases: []
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Functions/FUNC_80046B20.md`
- Replacement/current location: `ObsidianVault/Canon/Functions/FUNC_80046B20_unnamed.md`
- Archive reason: Existing function note; migrate only evidence-backed claims and link C source where available.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: FUNC_80046B20
type: function
address: 0x80046B20
confidence: CONFIRMED
tags: [function, gameplay, player, spawn, loader, milestone6, gap-0035]
---

# FUNC_80046B20 — initial player-block spawn / placement

> **The level-load player-spawn writer** (GAP-0035 layer 1). Signature **`FUNC_80046B20(a0 = player_block, a1 = scene_index)`** — fills the 168-byte player block `0x800a6500` from a **resident EXE start table** at `0x80077314 + index*12`. Located via a runtime WRITE-watch + execTrace → [[Experiment - Initial spawn write-watch]]. Lives in the level-load/init region (sibling of the LEVEL.RAW loader [[FUNC_80046330]]); called from scene-init [[FUNC_8005B714]].

## Signature & bounds
- Entry `0x80046b20` (prologue `addiu sp,sp,-40`; epilogue `0x80046c8c..0x80046ca4`).
- `a0` = player block base (CONFIRMED `=0x800a6500` at runtime); `a1` = scene/spawn index (CONFIRMED `=1` for LEVEL01); returns void.

## What it does (decoded + runtime-confirmed)
1. `lbu s2,0xa0(a0)` — **save the lives byte** `+0xa0` (`0x800a65a0`).
2. `jal 0x8005f7ac` (memset helper → BIOS `memset` `0xbfc02bb4`) — **zero the 168-byte (0xA8) block** (clears live/prev/anchor/velocity/flags). *(This is why a naive `findFirstWrite` reports the BIOS PC, not this function.)*
3. **Read the source record** `s0 = 0x80077314 + a1*12` (`a1*3<<2`), then store fields:
   | player offset | source | store PC |
   |---|---|---|
   | `+0x00` X | record **word0** | `0x80046b98` |
   | `+0x08` Z | record **word1** | `0x80046bac` |
   | `+0x04` Y | **computed:** `FUNC_80037A38(pos) − 0x100` (ground/floor height) | `0x80046bb8` |
   | `+0x10/14/18` prev/render copy | live X/Y/Z | `0x80046bd0/d4/d8` |
   | `+0x50/54/58` respawn anchor | live X/Y/Z | `0x80046c14/18`/`+0x58` |
   | `+0x20/+0x28/+0x78` heading | record **word2** | `0x80046bf0/c1c/c20` |
   | `+0x94=4`, `+0x98=0x11`, `+0x4c=0x80000000`, `+0x8e=0`, `+0x9e=0` | constants | `0x80046c04/bec/bfc/c10/c0c` |
   | `+0xa0` lives | **restored** from `s2` | `0x80046c00` |
4. A 64-iteration loop (`t1=0..63`, `t0+=132`) over array base `0x8009fd80` counting live entries into `+0x8e`; then clears a few `gp` globals.

## Source table `0x80077314` (resident, in the boot EXE) — per-scene, CONFIRMED
- **12-byte records** (3 words: X, Z, heading), indexed by `a1` (the scene index). Base VA `0x80077314` = **`SCUS_942.88` file offset `0x67b14`** (byte-exact RAM↔EXE cross-check).
- **Per-scene, byte-proven live for indices 1,2,3,4,6 + matched via save anchors for 7,10,11,15** ([[Experiment - Warp landing diversion]]): rec1=LEVEL01 (X `0x301f4`,Z `0x7855f`,head `0xdb1`); rec2 (-1580,-226854,0xfe7); rec3 (-16896,6632,0x2e6); rec4 (-289789,375937,0x857); rec6 (93783,-134554,0xbf7); … Records 1–17 are scene starts; 18+ is other data.
- **Disc-editable player-start lever** for any level: edit the record at `0x67b14 + scene_index*12` (X=word0, Z=word1, heading=word2; Y auto-snaps to ground).

## Caller / context — index = scene_id (CONFIRMED live)
Called at `0x8005baa4` (`a1 = s2 = a0`) from **inside scene-init [[FUNC_8005B714]]`(scene_id)`** — which also zeroes the `0x80082xxx` state cluster (`sw zero` to `0x80082390/2448/2294/2370/229c` right before the call) and seeds the resident noise cursor. **`index == current_scene_id [0x80082504]` — CONFIRMED**: diverting the level-select source `scene_table[1]` (`0x80077fa4`) before the cold-boot scene_id write makes the game load scene N and call this fn with `a1=N` reading table[N] (proven live for N=3,6,2,4, no crash → [[Experiment - Warp landing diversion]]). So **scene-init = state-zero + cursor-seed + player-spawn**, and **warp landings reuse this exact fn/table** indexed by the target scene_id (the cold initial spawn and a warp landing are one code path; only per-level values differ).
- **Index latch:** [[FUNC_8005B714]] is entered **once at the scene_id write**, latches `a0=scene_id` (`→s2`), triggers the CD load, **waits ~1000 frames**, then calls this fn at load-complete. The index is fixed at scene-init entry, **not** re-read at spawn — so a *late* `[0x80082504]` poke can't divert it and crashes (the [[Finding - Level-warp mechanism]] wall); the clean lever is the selection source before the write.

## Why static analysis missed it (resolves the 9-approach wall)
The store goes through the `a0` pointer arg (no absolute/gp/constant base — [[Gameplay - Initial Player Spawn]] approaches 1–9), and the first physical write is the BIOS memset. A runtime write-watch + `execTrace` on `a0/a1/s0` resolves both the writer and the source in one shot.

## Confidence
- Writer + `a0=player`/`a1=index` + field offsets — **CONFIRMED** (write-watch + execTrace; disasm).
- Source = resident EXE table `0x80077314[index]` (word0→X, word1→Z, word2→heading; Y computed) — **CONFIRMED** (ptr capture + value-match + EXE cross-check).
- `index == scene_id` / per-scene table / **reused for warp landings** — **CONFIRMED** (live diversion to scene 3,6,2,4 + 7-level save survey → [[Experiment - Warp landing diversion]]).

## Related
[[Experiment - Initial spawn write-watch]] · [[Experiment - Warp landing diversion]] · [[Gameplay - Initial Player Spawn]] · [[Gameplay - Player Spawn and Placement]] · [[FUNC_8005B714]] · [[FUNC_8003633C]] (per-frame integrator, takes over next frame) · [[FUNC_80046330]] · [[MEM - Player state 800A6500]] · `tools/trace_initial_spawn.py` · `tools/trace_warp_landing.py`
