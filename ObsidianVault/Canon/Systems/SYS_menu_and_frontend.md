---
kind: system
id: SYS_menu_and_frontend
aliases: [SYS_menu_and_frontend, MEMORY.BIN, frontend, "menu and frontend"]
created: 2026-07-09
updated: 2026-07-09
status: static_seen
confidence: medium
source_state: original_game
functions: []
memory: []
tables: []
constants: []
evidence: [EXP_2026-07-09_overlay_coverage]
src_paths: [analysis/overlay_symbols.json, analysis/traces/overlay_coverage.json]
patch_policy: safe_to_read
---

# SYS_menu_and_frontend — title / menu / save-load front-end (MEMORY.BIN)

## Purpose
The game's front-end (title screen, main menu, save/load, memory-card I/O) lives in the **MEMORY.BIN overlay**,
loaded into **Region-B `0x800B5788`** (distinct from the per-level Region-A `0x800B39A0`; the two are never
co-resident). Before OVL o0/o1 this was the biggest blind spot with **no Canon note** — 69 functions, only 5
named. This note maps its discovered structure. See [[EXP_2026-07-09_overlay_coverage]] and
[[SYS_overlays_and_runtime_loading]].

## Runtime coverage
The boot→title→menu→(memcard scan) path runs at the start of **every** `movies/go_to_end/` movie, so a single
pristine movie already exercises **44 of 69** MEMORY.BIN functions (`overlay_coverage.json`). Names are stored
in the per-overlay `analysis/overlay_symbols.json` (key `MEMORY`), NOT `re_symbols.sym` (overlays share load
addresses). Progress: **40 / 69 named** (every name evidence-gated: a PsyQ/BIOS callee, a call to a confirmed
anchor, or a jr-table/state-write signature).

## Architecture (named clusters)
- **Region-B base** `0x800B5788` (`region_b_overlay_base`).
- **Memory-card cluster:** `memcard_load_scan` `0x800BA668`, `save_block_builder_SCmagic` `0x800BAD08`,
  `memcard_save_write` `0x800BAF30`, `memcard_save_dispatch` `0x800BAFD4` (calls block-builder + writer),
  `memcard_load_dispatch` `0x800BB6F4`, `memcard_save_block_util` `0x800BA374`, `memcard_io_leaf` `0x800BA0A4`,
  `memcard_file_read` `0x800BB09C` (`sprintf`+`card_open/read/close`).
- **Async I/O event system** (PsyQ `*Event`): `card_event_setup` `0x800B9C4C` (`OpenEvent`+`EnableEvent`),
  `card_event_close` `0x800B9E98`, `card_event_poll[_038/22c/2d0]` (`TestEvent`).
- **VRAM image / font:** `vram_image_load[_dispatch]` `0x800B9A88`/`0x800BA4D4` (`LoadImage`+`DrawSync`),
  `vram_image_store` `0x800BB19C` (`StoreImage`), `font_rom_convert` `0x800B9900` (`Krom2RawAdd`).
- **Controller / cache:** `pad_init` `0x800BD730` / `pad_stop` `0x800BD788` (`ChangeClearPAD`),
  `overlay_flush_cache` `0x800BD818` (`FlushCache`), `overlay_load_finalize` `0x800BD7C0`.
- **Screens / menus:** `main_menu_state` `0x800B8AD4` (loops menu music + memcard), `menu_screen_dispatch`
  `0x800B7BA4` (jr-table), `frontend_state_dispatch` `0x800B96E4` (8-case jr-table), `frontend_menu_input_loop`
  `0x800B659C` (music + `sfx_menu_blip`), `frontend_scroll_sprite_screen` `0x800B7DA0` + `_driver` `0x800B9724`,
  `frontend_screen_music_once[_8988]`, sprite/texture draw helpers, `save_load_screen_main`/`_entry`.
- **Resident→front-end entry surface:** `0x800B6250` (`fmv_bin_load`+`scene_load_init`), `0x800B6594`
  (`scene_verb_dispatch`), `0x800B96E4`, `0x800BD518`, …

## Status / residual — 46 / 69 named; the remaining 23 have THREE concrete blockers
Not yet fully understood, and the blockers are named (not hand-waved) so completion is actionable:
1. **~5 census boundary artifacts** — the overlay census's `jal_target` heuristic split real functions at
   internal call sites, leaving false 8-byte "functions" (e.g. `0x800B9E90` is an event-close wrapper —
   reads `*0x80082418` + `CloseEvent` — that the census cut at 8 bytes). Needs an **overlay extent-override**
   pass (the analogue of the resident `extent_overrides.json` / RCA a5 fix) before these can be cleanly named.
2. **~7 call only unnamed overlay-internal helpers** (`0x800B97F8, 0x800BAA08, 0x800BAAD4, 0x800BD6D8`, …) —
   no PsyQ/anchor fingerprint; need per-function behavioral static RE.
3. **The big uncovered screen `0x800BD898` (sz 3408)** + a few others the pristine `go_to_end` movies never
   enter (they pass through the title but not into the options / load-game / save submenus). Needs a
   **menu-navigation movie** (scripted controller input into those screens) to get runtime evidence.
Per the evidence policy these stay `unknown` until one of the three is addressed; all are ranked in
`analysis/overlay_naming_priority.json`. Modding relevance: title/menu/save-screen edits. Related:
[[SYS_overlays_and_runtime_loading]] · [[SYS_function_census]] · [[HOOK_forbidden_patch_ranges]].
