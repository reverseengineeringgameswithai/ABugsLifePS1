---
kind: experiment
id: EXP_2026-07-08_understanding_campaign_u1
name: Understanding campaign u1 — runtime-driven naming of byte-matched-but-unknown functions
status: success
confidence: confirmed
source_state: evidence
validates: [SYS_function_census, SYS_decomp_substrate]
artifacts: [tools/verify_function_runtime.py, tools/apply_symbol_names.py, tools/naming_priority.py, symbols/re_symbols.sym]
---

# EXP_2026-07-08_understanding_campaign_u1

## Question
Byte-matching is at 31.3% of resident code but the game is 51% semantically unknown (530 unnamed
resident functions, 378 runtime-live-but-unnamed, **0 runtime-*proven* names**). Can the DuckStation
runtime API turn unnamed-but-executing functions into named, documented Canon functions — starting the
"proven" name count from 0 — reusing the existing naming pipeline?

## Verified runtime recipe (capability proven this session)
1. **Throwaway instance** (never the operator's port 2346): `tools/launch_repro_playback.sh --disc
   "Disney-Pixar A Bug's Life (v1.0).cue" --port 23460 --token debugger-1000 --config-dir /tmp/dsrepro_u1`
   → prints `READY`. Connect: `DebuggerClient("127.0.0.1",23460,"ws").authenticate("debugger-1000")` then
   `c.transport.sock.settimeout(30)`; assert `debugger.status.game_serial == "SCUS-94288"`.
2. **All required API methods are LIVE on the build** (verified by probe — the caveat methods exist):
   `debugger.functionBounds` ✓, `debugger.xrefsTo` ✓, `execTrace.addWatch`/`.run`/`.get` ✓,
   `accessLog.lastWriter` ✓, `movie.coverageToFrame` ✓ (errors only `-32005` without an active movie —
   present), `debugger.callFunction` ✓ (errors only `-32002` when not paused — present).
3. **Reaching a live-rendering level — use a SAVE STATE, not the from-boot movie.** The
   `flik_to_level01_stall` movie (4253 frames) ENDS during LEVEL01 *loading* (Flik unplaced,
   `0x800a6500 == 0`); free-running past it is non-deterministic (leaves the level / lands in the
   overlay region). `emulator.loadState {path: <abs>/ABL_looking_at_ramp_OG_Graphics.sav}` (pristine-disc
   state) drops straight into a live-rendering LEVEL01 (**Flik X `0x2e10d`**, render cluster executing —
   12 execTrace events across 2 frames with only the render cluster watched). **Re-arm all
   instrumentation after loadState.** Per-level states (`level02.sav`…`level_15.sav`) + enemy/render
   states are available.
4. **Per-function evidence:** `execTrace.addWatch {pc, capture:["a0","a1","a2","ra"]}` → `execTrace.run
   {frames:N}` → `.get` (hit counts + entry registers; **event `pc` is a hex STRING**) · `functionBounds`
   (extent; trust `confidence:"exact"` AND `mergedRegion:false`) · `xrefsTo` (callers) · `callFunction`
   (I/O; paused; mutates → throwaway only) · `accessLog.lastWriter`/`addWatch` (r/w set) ·
   `transferLog.resolve` (disc provenance) · `getGteState`/`gpu.pickObject` (render fns).
5. **Name it:** JSON manifest `{"address","name","tier":"proven|inferred|temporary","evidence":[...],
   "rationale":"..."}` → `python3 tools/apply_symbol_names.py <manifest> --dry-run` then apply (upgrades
   `FUNC_`/`provisional_`, requires the addr be a resident fn START, requires `evidence` for
   proven/inferred, leaves `.bak`) → `tools/validate_symbol_map.py` → `tools/function_census.py`
   (flips `unknown`→`game`) → refresh `tools/naming_priority.py`.

## Target set
The render/geometry cluster (bracketed by named dispatchers + GTE prims, all `dynamic`):
`0x8002d674` (9756 B; callers `dirt_object_dispatch`+`scene_geometry_draw_dispatcher`; calls
`SetRotMatrix`/`SetTransMatrix`/`RotTransPers` → per-object 3D mesh transform+draw), `0x8003f938`
(4288 B, matched asm; caller `scene_render_driver`; calls `RotTransPers4` → render-pass geometry),
`0x800409f8` (4220 B, matched asm), `0x800153d0`, `0x800163e0`, `0x800526fc`.

## u1.1 result — loop PROVEN, 0 → 4 named
Scanned the 49 matched+dynamic+unnamed candidates with `execTrace` in the live LEVEL01 scene: **22 fired
in 4 frames** with entry-register context. Named 4 with converged evidence (byte-matched + dynamic +
unambiguous call-graph + register semantics), via `apply_symbol_names.py` (proven tier):
- `0x8003f938` → **render_mesh_transform** (caller `scene_render_driver`; `SetRotMatrix`/`SetTransMatrix`/
  `RotTransPers4`; scratchpad `0x1f8003xx` args).
- `0x8004b940` → **mover_actor_update** (caller `mover_updater`; `player_movement_collision_integrator`/
  `atan2_heading`/`spawn_drop`; actor-region `a0`).
- `0x8005cd2c` → **gameplay_effect_spawner** (caller `gameplay_state_machine`; `spawn_fx_object`/
  `play_sound`/`contact_object_spawn_full`; 11-iteration spawn loop).
- `0x8007403c` → **consume_flag_37** (read-and-clear latch on `obj+0x37`→`+0x38`; full 4-instr body).

**Metric:** proven names **0 → 4**; resident `unknown` **530 → 526**; symbol map 838 → 842 (valid);
`function_census` flips all 4 `unknown`→`game`; SHA-1 unaffected (naming is data-only); safe suite 78 green.
Canon `FUNC_<addr>_<name>.md` written for all 4. (Register `pc` is a hex STRING — count with that in mind.)

## u1.2 result — render cluster (0 → 6 total named)
Loading an enemy scene (`bee.sav`) activated the object-render dispatchers (terrain-only `ABL_looking_at_ramp`
never fires them). Named 2 more (proven):
- `0x8002d674` → **object_mesh_draw** — the **largest resident unknown (9756 B)**; both object dispatchers
  (`dirt_object_dispatch`, `scene_geometry_draw_dispatcher`) call it; `SetRotMatrix`/`SetTransMatrix`/
  `RotTransPers`; runtime-confirmed drawing objects (3 hits/3 frames, `a0`=object data).
- `0x800526fc` → **results_screen_render** — callees `hud_draw_sprite_tile`/`hud_draw_glyph`/
  `result_draw_glyph_dim`/`result_upload_anim_frame`/`play_sound`.
**Cumulative: resident `unknown` 530 → 524; proven names 0 → 6; symbol map 838 → 844.** Suite 78 green.

## Continuation (u1.3–u1.5)
- **Deferred (need distinguishing analysis, not imprecise names):** `0x800153d0` (4112 B) + `0x800163e0`
  (3836 B) — near-identical render-geometry workers under `scene_geometry_draw_dispatcher` (scratchpad
  staging + `VectorNormal`); need body-diffing to name distinctly.
- The `0x80072xxx` cluster (shared `a0=0x800890c8`, HW I/O `0x1f801128`, unnamed callees) — recurse:
  identify `0x800890c8` first. `0x800409f8` (SquareRoot0+VectorNormal vector math). `0x800649a0`
  (DMACallback+SetIntrMask → DMA/IRQ).
- u1.3 SYS gaps (movement/camera/player).

## u1.4 — deferred byte-% items: `functionBounds` says SKIP all (confirmed)
- `0x8002b428`: `confidence:low, mergedRegion:True` — *"8740 B exceeds the plausible single-function
  maximum (8192); almost certainly merges several routines."* Confirmed over-merge → NOT banked
  (the tool + memory flag overrule the structural "1 prologue / 1 jr ra" appearance).
- `0x800498ac`, `0x80058af8`: reported `exact`, but each contains a separately-referenced address (e.g.
  the **named** `scatter_velocity_builder 0x800593e8` inside `0x80058af8`) — banking them would absorb a
  named symbol (the `test_every_text_symbol_is_a_census_start` failure mode). Needs sub-function
  splitting = out of scope. **No safe byte-% available here without the excluded splitting/over-merge work.**

## u1.3 — SYS-note gaps filled
Authored [[SYS_movement_and_physics]], [[SYS_player]], [[SYS_camera]] (synthesis of already-named
member functions + `src_re` decomp + runtime call-graph). Named `camera_region_query` 0x800376a0.

## u1.5 — scaled naming by the priority queue (batch04, 12 names)
Ranked the 214 unknown+dynamic functions that have ≥1 NAMED neighbour and named 12 with clear
call-graph roles (proven where SDK callees are definitive, inferred for gameplay call-graph):
`cd_subsystem_init` 0x80045d6c, `display_env_setup` 0x8003912c, `boot_video_audio_init` 0x80039970,
`gameplay_frame_render` 0x8004f480, `spu_voice_key_onoff` 0x80043500, `frame_present` 0x80039a70,
`sound_voice_trigger` 0x800438a8, `effect_mesh_transform` 0x80022fe0, `queue_draw_prim` 0x80026d78,
`scene_flow_dispatcher` 0x8004fca0, `player_contact_response` 0x80047284, `level_chunk_loader` 0x8005d654.

## u1.5 CLOSED — clean (distinct-role) naming queue worked down
Two more batches (batch05 12 + batch06 4) took the RCnt/interrupt cluster (decoded: `0x80072xxx` =
root-counter/interrupt subsystem, timer reg `0x1f801128`, state `0x800890c8` — runtime BSS, no disc
provenance) and the remaining distinct-role functions: `rcnt_interrupt_install/remove`,
`draw_textured_quad`, `sound_positional_voice`, `sound_system_init`, `cd_find_file_by_name`,
`scene_load_init`, `actor_skinned_update`, `level_texture_upload`, `load_named_file`,
`level_load_chunks`, `pickup_effect_dispatch`, `contact_pickup_sfx`, `respawn_collision_reset`,
`projectile_aim`, `loadscreen_image_setup`.

**Close accounting (actual conclusion, not the nominal 40–60):** of the 343 remaining unknown+dynamic
functions — **134 have no named neighbour** (need full-body disasm), **54 are tiny <64 B helpers**, and
the ~52 with an SDK-callee signal are **dominated by a homogeneous GTE mesh-transform cluster**
(`SetRotMatrix`/`RotTransPers`/`RotAverage4`, ~20+ near-identical-role fns) that needs **body-diffing to
name distinctly** — quick call-graph naming would only produce low-value duplicate names. So the
distinct-role, cleanly-nameable queue is exhausted (same discipline as the v4.5 byte-% close). u1.5 is
**CLOSED on actual conclusion**; the remainder is a documented deep-analysis tail, not a forced count.

## Campaign u1 totals
**Resident `unknown` 530 → 495 (35 named); proven-tier names 0 → 15; symbol map 838 → 873.** SHA-1
unaffected (naming is data-only); safe suite 78 green throughout. Canon `FUNC_` notes for the
u1.1/u1.2 headline functions; batches recorded here + in `symbols/re_symbols.sym` (Canon `FUNC_`
promotion is a lightweight follow-up). **Deep-analysis tail (continuation):** the ~20+ GTE
mesh-transform cluster (body-diff by object type), 134 no-neighbour fns (disasm), 54 tiny helpers, and
the `0x800153d0`/`0x800163e0` look-alike pair.

## Evidence / links
[[SYS_function_census]] · [[DuckStation_API_Index]] · [[EXP_2026-07-08_c_decompilation_campaign_v4]].

> **Closed (2026-07-10):** u1 completed as recorded and was continued by u2/u3 (resident unknown 530→344→0-unknown-class per analysis/re_campaign_status.json).
