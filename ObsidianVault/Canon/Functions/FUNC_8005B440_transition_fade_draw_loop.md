---
kind: function
id: FUNC_8005B440
aliases:
- FUNC_8005B440
- '0x8005b440'
- transition_fade_draw_loop
address: '0x8005b440'
name: transition_fade_draw_loop
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- contact_cursor_transition_reset
- hud_draw_sprite_tile
- queue_draw_prim
- seed_cursor_state_jump_dispatch
- store_four_bytes
- wait_for_frame_sync_flag
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch06_residual.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch06_residual.json
patch_policy: safe_to_read
---

# FUNC_8005B440 - transition_fade_draw_loop

## Purpose
Standalone routine running a 24-frame sprite/fade draw loop during a transition

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- full prologue/epilogue; 24-iter loop calling hud_draw_sprite_tile, queue_draw_prim, wait_for_frame_sync_flag, seed_cursor_state_jump_dispatch; called by fmv_bin_load

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch06_residual.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
