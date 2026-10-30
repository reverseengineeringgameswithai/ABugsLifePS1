---
kind: function
id: FUNC_800584F8
aliases:
- FUNC_800584F8
- '0x800584f8'
- spawn_drop_burst_5_type79
address: '0x800584f8'
name: spawn_drop_burst_5_type79
status: byte_matched
confidence: confirmed
source_state: original_game
tier: inferred
calls:
- play_sound
- sfx_proximity_priority_gate
- spawn_drop
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch02.json
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch02.json
- src/main/800584f8_spawn_drop_burst_5_type79.c
patch_policy: safe_to_read
---

# FUNC_800584F8 - spawn_drop_burst_5_type79

## Purpose
Spawns 5 type-79 drops with a white positional effect and sound 5 (fixed spawn burst)

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- 5-iter spawn_drop(a3=79) from object xyz; sfx_proximity_priority_gate(a3=0xffffffff,30); play_sound(5,object)

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
