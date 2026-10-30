---
kind: index
id: OVERLAY_CAMPAIGN_STATUS
aliases: [OVERLAY_CAMPAIGN_STATUS, "Overlay Campaign Status", "overlay resume", "overlay handoff"]
created: 2026-07-09
updated: 2026-07-09
status: closed_with_residual
related: [SYS_overlays_and_runtime_loading, SYS_menu_and_frontend, EXP_2026-07-09_overlay_coverage]
---

# Overlay Understanding Campaign — status & resume

**Where we are: overlay CODE 158 fns, 158 named (100%).** Substrate + tracing + naming are done. Full record: [[SYS_overlays_and_runtime_loading]] (mechanics + code
semantics), [[SYS_menu_and_frontend]] (MEMORY.BIN front-end), [[EXP_2026-07-09_overlay_coverage]] (the tracing
method). Auto-memory: `overlay-understanding-campaign`.

## What's built (reusable)
- **Name store:** `analysis/overlay_symbols.json`, keyed by `(overlay,address)` — overlays share load base
  `0x800B39A0`, so `re_symbols.sym` can't name them. Edit via `tools/apply_overlay_names.py <manifest.json>`;
  check with `tools/validate_overlay_symbols.py`; the census reads it (`tests/test_overlay_symbols.py` guards).
- **Coverage:** `tools/trace_overlay_coverage.py --relaunch` replays each pristine `movies/go_to_end/*.movie.json`
  on the **reproducible** instance (`tools/launch_repro_playback.sh` — a from-boot movie desyncs to 0 coverage
  without it) → `analysis/traces/overlay_coverage.json`. **Pristine media only, never modded saves.**
- **Ranking:** `analysis/overlay_naming_priority.json`. **Data detector:** the census reclassifies overlay
  spans with no `jr ra`/`jal` as data (pointer tables / filename strings / headers) — don't try to name those.

## Residual A — functions the current movies NEVER hit

**Only ONE level run + one menu run remain** — LEVEL01/05/07 were all closed STATICALLY (no run needed):
- **LEVEL07** `0x800B3C94` — 2-insn entry stub → `state_writer_arg_entry`.
- **LEVEL05_LEVEL1** `0x800B3AFC` — a pure **constant initializer** (16 stores of tuning values into the
  overlay state block, 0 calls) → `level05_overlay_param_init`; its behavior is fully determined by its bytes.
- **LEVEL01_LEVEL** `0x800B3F54` — NOT a function: a 55-word **gp-global pointer table** (r2 mislabel; a
  jal-looking word with an out-of-RAM target fooled the detector) → reclassified DATA (census
  `_OVERLAY_DATA_OVERRIDE`).

- **LEVEL04_LEVEL** `0x800B3F3C` — **COVERED** by the 100% LEVEL04 run (`movies/100% Runs/LEVEL04.movie.json`):
  fired 40x from scene_verb_dispatcher (scene-verb `0x68`) → `level04_complete_handler`. It calls
  `level_complete_finale` + `result_upload_anim_frame` + `transition_finalizer_subsystem_reset` = the
  end-of-level outro. **CORRECTION:** LEVEL04 has NO boss (bosses are 03/06/09/12/15); the resident
  `0x8004DA94` was mislabeled `boss_defeat_finale` and is renamed **`level_complete_finale`** (called by the
  completion path of 6 non-boss level overlays 01/02/03/04/05/07).

**All 3 originally-"movie-blocked" MEMORY fns are RESOLVED (u3 live capture, 2026-07-09):**
- `0x800BAA08` → **`save_string_glyph_encode`** (live during Save; ASCII→glyph-tile encoder, caller
  `save_block_builder_SCmagic`).
- `0x800BAFCC` → **`memcard_slot_state_get`** (live during Save/Load; 8-byte getter of `0x80082418`, caller
  `memcard_slot_manage`).
- `0x800BD898` → **NOT a function** — an 844-word data table (0 jr-ra/jal; never executes across Save/Load/
  Options/Movie-Clips/level-select). Reclassified DATA (census `_OVERLAY_DATA_OVERRIDE`).

**➡ NOTHING is movie-blocked anymore.** Every level overlay is covered or statically closed; the entire
front-end (title/menu/Movie-Clips/Options/Save/Load memcard path) is named. Confirmed live: the misc screens
run only already-named front-end fns (`main_menu_state`, `menu_nav_cursor`, `frontend_menu_input_loop`, …).

## Residual B — closed (2026-07-09)
The final three covered functions were statically reversed and byte-matched from C:

~~`LEVEL02_LEVEL1 0x800B48F4`~~ **named u3-3** (`color_channel_lerp`, 40 live hits — it IS code) ·
~~`LEVEL06_LEVEL 0x800B3BBC`~~ **named u3-3** (`transition_handler_arg_entry`, called live from the resident
scene-verb dispatcher) · `LEVEL06_LEVEL1 0x800B3AF4` = `level06_select_grid_offset` ·
`MEMORY 0x800BA1F0` = `memcard_directory_load_for_slot` · `MEMORY 0x800BD6D8` =
`memcard_ack_card_change`. See `analysis/naming/ovl_u5_tail.json`.

## Resume procedure (when new runs exist)
1. `python tools/trace_overlay_coverage.py --relaunch --port 23460 --token debugger-1000 --only LEVEL04`
   (or omit `--only` for all) → refreshes `overlay_coverage.json`.
2. For each newly-covered unnamed fn: fingerprint its resident calls (r2 disasm → resolve via census +
   `re_symbols.sym`) → write a manifest `{overlay,address,name,tier,evidence,rationale}` →
   `python tools/apply_overlay_names.py <manifest>.json` → `python tools/function_census.py` →
   `python tools/overlay_naming_priority.py`.
3. Verify: `tools/validate_overlay_symbols.py`, `tools/build_overlay.py` (blobs SHA-valid),
   `tools/run_safe_tests.py`, `tools/validate_vault.py --check`. Update this note + the auto-memory.

## Also open (separate sub-tasks)
- ~~LEVEL11–15 overlay extraction~~ **RESOLVED (u2 survey, 2026-07-09): LEVEL11–15 do not exist on the
  disc** — the game ships 11 level directories (`REBUILD/abl.xml`; a raw scan of the .bin finds zero
  LEVEL11+ strings). The logical scenes 11–15 reuse the Region-A swap buffer with the existing LEVEL00–10
  blobs. All overlay blobs are already extracted; nothing to do.
- **o5:** continue byte-matching understood overlay functions; `overlay_decomp_progress.json` is now 15 matched C.

Related: [[SYS_overlays_and_runtime_loading]] · [[SYS_menu_and_frontend]] · [[SYS_function_census]] ·
[[EXP_2026-07-09_overlay_coverage]] · [[DuckStation_API_Index]].
