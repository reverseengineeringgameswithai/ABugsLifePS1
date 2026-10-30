---
kind: function
id: FUNC_80057404
aliases:
- FUNC_80057404
- '0x80057404'
- clear_gameplay_pool_on_reset
address: '0x80057404'
name: clear_gameplay_pool_on_reset
status: byte_matched
confidence: confirmed
source_state: original_game
tier: inferred
calls:
- memset
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch06_residual.json
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch06_residual.json
- src/main/80057404_clear_gameplay_pool_on_reset.c
patch_policy: safe_to_read
---

# FUNC_80057404 - clear_gameplay_pool_on_reset

## Purpose
Standalone reset routine clearing a ~3.5KB gameplay pool buffer + two state globals on reset/respawn

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- prologue/epilogue; memset(0x800B0D18,3584), zeroes 0x8008234C and gp+1192; callers gameplay_state_reset_cursor_seed, respawn_transition_state_handler

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch06_residual.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
