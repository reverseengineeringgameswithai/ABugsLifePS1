---
kind: experiment
id: Experiment_-_Warp_landing_diversion
created: 2026-07-08
updated: 2026-07-08
status: legacy_imported
confidence: confirmed
legacy_source: ObsidianVault/Experiments/Experiment - Warp landing diversion.md
aliases:
  - "Experiment - Warp landing diversion"
---

# Experiment — live warp-landing capture (GAP-0035 live half)

> Migrated from `ObsidianVault/Experiments/Experiment - Warp landing diversion.md` during the 2026-07-08 vault completion pass. Original action: `convert_to_experiment`. Reason: Experiment note should preserve proof artifacts and link Canon claims it validates.

# Experiment — live warp-landing capture (GAP-0035 live half)

> Closes the GAP-0035 live-warp half: **a scene transition into a NON-LEVEL01 level lands via the SAME spawn path as the cold LEVEL01 spawn** ([[Experiment - Initial spawn write-watch]]) — scene-init [[FUNC_8005B714]]`(scene_id)` → [[FUNC_80046B20]]`(player, scene_id)` reading the resident table `0x80077314 + scene_id*12`. Confirmed live for scene indices **3, 6, 2, 4** (no crash), plus a 7-level save survey. Runtime, local-only ([[DuckStation Fork Reproducibility]] / GAP-0001). Driver: `tools/trace_warp_landing.py`.

## Part A — safe per-level survey (anchor == table[scene_id])
Load each per-level save, read `current_scene_id [0x80082504]` and the respawn anchor `0x800a6550/58`, cross-check against the spawn table `0x80077314 + scene_id*12`. The anchor is written only by [[FUNC_80046B20]] (spawn) and `0x80054c90` (checkpoint); a fresh save's anchor == table[scene_id] ⇒ [[FUNC_80046B20]] spawned it there.

| save | `[0x80082504]` (=stage) | anchor X,Z | table[idx] X,Z | |
|---|--:|---|---|---|
| level03.sav | 2 | -1580, -226854 | -1580, -226854 | ✓ exact |
| level02.sav | 3 | -16896, 6631 | -16896, 6632 | ✓ |
| level04.sav | 6 | 93783, -134554 | 93783, -134554 | ✓ exact |
| level_10.sav | 7 | 63709, 56801 | 63740, 56996 | ✓ (≈, mid-level drift) |
| level05.sav | 10 | -3623, -273237 | -3625, -273246 | ✓ |
| level_06.sav | 11 | 44293, 75030 | 44293, 75030 | ✓ exact |
| level_15.sav | 15 | 178426, 150035 | 178426, 150035 | ✓ exact |

⇒ the spawn table is **per-scene**, indexed by `[0x80082504]`; in every save `scene_id == stage` (filenames are operator labels, not the index). `tools/trace_warp_landing.py --survey`.

## Part B — live diversion (the clean lever)
The cold-boot load does **NOT** use the in-game warp orchestrator [[FUNC_8005222C]] (read/write-watch on `0x80082504` across the boot movie showed **no `19→0→restore` writes**). Instead the shell SM selects from the level-select table:
```
0x8004fdb8  lw v0, 0x7fa0(at)     ; v0 = scene_table[0x80077fa0 + idx*4]   (LEVEL01 = idx1 → value 1)
0x8004fdc0  sw v0, 0x2504(at)     ; current_scene_id = v0                    (frame ~3486)
0x8004fdf0  …                     ; scene-init FUNC_8005B714(scene_id) — LATCHES index, loads, spawns
```
**Method (`tools/trace_warp_landing.py --target N`):** replay `flik_to_level01_stall.mv` from boot, fast-forward to frame ~3000 (scene_id still 0), then **poke `scene_table[1]` (`0x80077fa4`) = N** *before* the front-end reads it at ~3486. The game then natively writes `scene_id=N`, loads stage N, and spawns table[N]. Watches: `execTrace` at `FUNC_8005B714`/`FUNC_80046B20`/`0x80046b88`; write-watch player block.

### Results — 4 independent clean landings
| target | scene/stage | `FUNC_8005B714` a0 | spawn a1 | src s0 (= `0x80077314+N*12`) | live X,Z (= table[N]) | landing pc | crash |
|--:|--:|--:|--:|---|---|---|:--:|
| 3 | 3 / 3 | 3 | **3** | 0x80077338 ✓ | -16896, 6632 ✓ | 0x8003e13c | **no** |
| 6 | 6 / 6 | — | **6** | 0x8007735c ✓ | 93783, -134554 ✓ | 0x8004fea4 | **no** |
| 2 | 2 / 2 | — | **2** | 0x8007732c ✓ | -1580, -226854 ✓ | 0x80010884 | **no** |
| 4 | 4 / 4 | — | **4** | 0x80077344 ✓ | -289789, 375937 ✓ | 0x80064a70 | **no** |

For target 3 the full player block was captured: the **same `0x80046bxx` field writes** as the cold LEVEL01 spawn — live `+0x00/04/08`, render copy `+0x10/14/18`, anchor `+0x50/54/58`, heading `+0x20/28/78` (=0x2e6), `+0x4c=0x80000000`, `+0x94=4`, `+0x98=0x11`, velocity `+0x1c=0` (zeroed), lives `+0xa0` preserved — all from table[3]. **No warp-specific reset; the cold spawn and warp landing are one code path.**

## Mechanism (resolves the GAP-0035 "wrong-context crash")
`FUNC_8005B714` is entered **once at the scene_id write** (frame ~3486) with `a0=scene_id`, **latches the index** (`a0→s2`), triggers the CD load, **waits ~1000 frames** for it to finish, then calls `FUNC_80046B20(player, s2)` at load-complete (frame ~4518). So the index is fixed at scene-init **entry**, not re-read at spawn time. ⇒
- A **late** `[0x80082504]` poke (after ~3486) does **not** divert the spawn (a1 stays the latched value) and leaves `scene_id` inconsistent with the loaded stage → **crash to BIOS `0xbfc0d8e8`** (the documented [[Finding - Level-warp mechanism]] wall, reproduced here).
- The **clean** lever is the selection source `scene_table[1]` (before ~3486) — proven above.
- Halting note: execute breakpoints and `execTrace stop_on_hit` do **NOT** halt during movie playback (`advanceFrames`/`resume` run through them); only the non-halting watches record. So the capture uses watches + a pre-write poke, never a halt.

## Confidence
- [[FUNC_80046B20]] reused for non-LEVEL01 landings (live a1 = diverted index) — **CONFIRMED** (4 indices + survey).
- Index = `current_scene_id [0x80082504]` = level-select value `scene_table[idx]`; `scene_id == stage` here — **CONFIRMED** (changed the selection → spawn a1 followed).
- Destination = table[index] (X,Z,head; Y computed) + same reset side-effects as cold — **CONFIRMED**.
- Clean landing (no crash) for diverted cold-boot loads — **CONFIRMED** (4/4).
- In-game (mid-level) warp via [[FUNC_8005222C]] orchestrator — **still crash-prone** from mid-gameplay (different trigger path; the *landing* spawn is identical). The cold-boot diversion is the verified clean route.

## Related
[[Experiment - Initial spawn write-watch]] · [[FUNC_80046B20]] · [[FUNC_8005B714]] · [[Gameplay - Warp and Level Transition]] · [[Gameplay - Initial Player Spawn]] · [[Finding - Level-warp mechanism]] · [[MEM - Player state 800A6500]] · [[API - accessLog]] · [[API - execTrace]] · [[API - movie]] · `tools/trace_warp_landing.py`
