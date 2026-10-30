---
kind: system
id: SYS_scene_asset_load_graph
name: Scene to asset and overlay load graph
status: live_confirmed
confidence: confirmed
source_state: original_game
memory:
  - MEM_EVENT_SYSTEM_GLOBALS
evidence:
  - EXP_2026-07-12_phase3_architecture_maps
  - analysis/phase3_scene_asset_graph.json
  - analysis/phase2_completion_oracle.json
src_paths:
  - tools/phase3_scene_asset_graph.py
---

# SYS_scene_asset_load_graph

## Confirmed original-game contract

The whole campaign's resource routing lives in three ASCII tables in the
resident EXE. Each was located by scanning the pristine image for level-ish
strings and then finding the code that materializes the table base.

| Table | Address | Shape | Consumer |
|---|---|---|---|
| scene asset | `0x8001AD0C` | 15 × `0x10`, `"levelNN\levelXY"` | `0x8003CFDC` in `resource_id_dat_load_dispatcher` (`0x8003CF2C`) |
| GFX loading screen | `0x8001AE98` | 15 × `0x10`, `"gfx\levelXY.raw"` | `0x8003F4B8` in `switch_dispatch_struct_by_index` (`0x8003F3B4`) |
| level BIN | `0x8001B174` | `level1.bin`..`level3.bin` + `level.bin` | `0x80046718` in `level_file_path_build` (`0x80046618`) |

**The load law:** row index = **scene_id − 1** (scene id is the u32 at
`0x80082504`). Within a row, the **disc directory** (`levelNN`) selects the
*overlay pair* — `LEVELNN_LEVEL` / `LEVELNN_LEVEL1` in the function census —
while the **asset prefix** (`levelXY`) selects *which sub-level's data and
loading screen* load out of it.

This is why **disc directory numbers do not track scene ids**: three sub-levels
share one directory, so scene 11 (Birdnest) loads `level02\level4b`. Any tool
that "simplifies" the mapping to `level{scene_id}` is wrong; a regression test
pins the mismatch.

## Full campaign map

| Scene | Asset entry | Loading screen | Overlays | Stage (Phase-2 movie) |
|---|---|---|---|---|
| 1 | `level01\level1a` | `gfx\level1a.raw` | LEVEL01 | Anthill |
| 2 | `level03\level1b` | `gfx\level1b.raw` | LEVEL03 | Council Chamber |
| 3 | `level02\level1c` | `gfx\level1c.raw` | LEVEL02 | Tunnels |
| 4 | `level06\level2a` | `gfx\level2a.raw` | LEVEL06 | City Entrance |
| 5 | `level10\level2b` | `gfx\level2b.raw` | LEVEL10 | City Square |
| 6 | `level01\level2c` | `gfx\level2c.raw` | LEVEL01 | Cliffside Canyon |
| 7 | `level04\level3a` | `gfx\level3a.raw` | LEVEL04 | Clover Forest |
| 8 | `level05\level3b` | `gfx\level3b.raw` | LEVEL05 | Riverbed Flight |
| 9 | `level04\level3c` | `gfx\level3c.raw` | LEVEL04 | Anthill Part Two |
| 10 | `level07\level4a` | `gfx\level4a.raw` | LEVEL07 | Riverbed Run |
| 11 | `level02\level4b` | `gfx\level4b.raw` | LEVEL02 | Birdnest |
| 12 | `level03\level4c` | `gfx\level4c.raw` | LEVEL03 | The Tree |
| 13 | `level09\level5a` | `gfx\level5a.raw` | LEVEL09 | Battle Arena |
| 14 | `level08\level5b` | `gfx\level5b.raw` | LEVEL08 | Bug Bar |
| 15 | `level05\level5c` | `gfx\level5c.raw` | LEVEL05 | Canyon Showdown |

## Why this is trustworthy

The decode is **cross-verified against independent runtime evidence**: every one
of the 15 rows resolves to the scene id that the corresponding Phase-2
`go_to_end` from-boot movie actually reached (`target_scene` in
`analysis/phase2_completion_oracle.json`). Static decode and observed replay
agree on all 15 — neither was derived from the other.

## Exceptional Training route

**Training (scene 17) is outside the 15-row campaign table, but it is now mapped.**
The resident dispatcher uses table `0x8001AFB0`, index 16, and transfers to
`0x8003CFC4`. That path owns the hash-pinned `LEVEL00` data and
`GFX/TRAINING.RAW`. `LEVEL00/LEVEL.BIN` is a four-byte sentinel, not a Region-A
code overlay; Training therefore uses the resident/shared path plus `LEVEL00`
resources. The exact assets and hashes are retained under `exceptional_routes`
in `analysis/phase3_scene_asset_graph.json`.

`LEVEL10` has only a single overlay (`LEVEL10_LEVEL`) in the census where every
other directory has a `_LEVEL` / `_LEVEL1` pair — unexplained, worth a look when
City Square is campaigned.

The same report makes unload ownership explicit: exit leaves actor, plant, and
contact bytes stale; the next resource load overwrites world-owned records while
session-owned player fields carry across. Training, Bug Bar's empty actor roster,
and the four delayed-health stages are represented as explicit exceptions.

## Overlay boundaries (Phase-3, joined 2026-07-13)

The scene-asset graph says *which* overlay each scene loads. `analysis/phase3_overlay_map.json`
(`tools/phase3_overlay_map.py`) joins that with the overlay RAM ranges, function
counts, and entry points — four artifacts that had never been joined.

- **Region A** `0x800B39A0` = the per-level **LEVEL*.BIN swap buffer**.
- **Region B** `0x800B5788` = **MEMORY.BIN** (front-end / shared).
- Overlay RAM window: `0x800B39A4..0x800BE5E8`; shared `$gp` `0x80081D98`.

⚠️ **An address in the overlay window has NO fixed meaning.** Every `LEVEL*.BIN`
overlay maps to the **same** base `0x800B39A0` — region A holds a *different* level's
overlay on each load. So an entry VA there belongs to **whichever overlay is
currently resident** (the scene id `0x80082504` selects it), not to any one level.
The 42 region-A entry points are therefore listed **once as shared**, not faked
per-level; only region B (MEMORY.BIN, a distinct base) has unambiguous entries.

**For a mod:** a cave that reads or writes an overlay-window address must condition on
the loaded overlay. `mod/hook_caves.yaml` models overlays **not at all** — it is
resident-EXE only, so its bounds checks do not protect against an overlay collision.

## Regeneration

`python3 tools/phase3_scene_asset_graph.py` (needs the local EXE at
`REBUILD/files/SCUS_942.88`; `file_off = vaddr − 0x8000F800`).
Guarded by `tests/test_phase3_scene_graph.py`.
