---
kind: function
id: FUNC_8003F5FC
aliases:
- FUNC_8003F5FC
- '0x8003f5fc'
- reset_visual_sprite_object_pool
address: '0x8003f5fc'
name: reset_visual_sprite_object_pool
status: byte_matched
confidence: confirmed
source_state: original_game
tier: inferred
calls: []
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch06_residual.json
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch06_residual.json
- src/main/8003f5fc_reset_visual_sprite_object_pool.c
patch_policy: safe_to_read
---

# FUNC_8003F5FC - reset_visual_sprite_object_pool

## Purpose
Standalone routine zeroing the stride-836 visual_sprite_object_pool table

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- jr ra; loop clears stride-836 record array at 0x8009C870 (visual_sprite_object_pool); caller resource_load_buffers_reset

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch06_residual.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
