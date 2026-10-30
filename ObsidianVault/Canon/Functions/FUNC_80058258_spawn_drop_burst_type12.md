---
kind: function
id: FUNC_80058258
aliases:
- FUNC_80058258
- '0x80058258'
- spawn_drop_burst_type12
address: '0x80058258'
name: spawn_drop_burst_type12
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
- src/main/80058258_spawn_drop_burst_type12.c
patch_policy: safe_to_read
---

# FUNC_80058258 - spawn_drop_burst_type12

## Purpose
Fixed 16-drop burst of type 12/13 with positional SFX 30 and sound 13 (particle/gib burst)

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- 16-iter spawn_drop(coords s1+0/4/8, type=0xc|parity); sfx_proximity_priority_gate(id=30,a3=0x80c0); play_sound(13,s1)

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
