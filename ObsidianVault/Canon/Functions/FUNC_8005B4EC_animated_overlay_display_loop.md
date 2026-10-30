---
kind: function
id: FUNC_8005B4EC
aliases:
- FUNC_8005B4EC
- '0x8005b4ec'
- animated_overlay_display_loop
address: '0x8005b4ec'
name: animated_overlay_display_loop
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- contact_cursor_transition_reset
- display_env_setup
- hud_draw_sprite_tile
- play_sound
- queue_draw_prim
- store_four_bytes
- wait_for_frame_sync_flag
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch05_final.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch05_final.json
patch_policy: safe_to_read
---

# FUNC_8005B4EC - animated_overlay_display_loop

## Purpose
Blocking frame-synced routine drawing HUD sprite tiles/primitives over an animated countdown (screen/overlay display sequence)

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- frame loop driving wait_for_frame_sync_flag with countdown timers (s4=24); callees hud_draw_sprite_tile, display_env_setup, queue_draw_prim, play_sound; state flags 0x80089234

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch05_final.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
