---
kind: function
id: FUNC_80039A20
aliases:
- FUNC_80039A20
- '0x80039a20'
- graphics_reset_teardown
address: '0x80039a20'
name: graphics_reset_teardown
status: byte_matched
confidence: confirmed
source_state: original_game
tier: inferred
calls:
- DrawSync
- ResetGraph
- StopCallback
- VSync
- vsync_wait_glue_e8c4
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch01.json
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch01.json
- src/main/80039a20_graphics_reset_teardown.c
patch_policy: safe_to_read
---

# FUNC_80039A20 - graphics_reset_teardown

## Purpose
Drains GPU/vsync, stops callbacks, ResetGraph(3): graphics subsystem teardown

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- caller scene_flow_dispatcher
- DrawSync(0)x2, VSync(0)x2, StopCallback(), vsync_wait_glue, ResetGraph(3)

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
