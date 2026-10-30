---
kind: function
id: FUNC_800581C8
aliases:
- FUNC_800581C8
- '0x800581c8'
- spawn_drop_burst
address: '0x800581c8'
name: spawn_drop_burst
status: byte_matched
confidence: confirmed
source_state: original_game
tier: inferred
calls:
- play_sound
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
- src/main/800581c8_spawn_drop_burst.c
patch_policy: safe_to_read
---

# FUNC_800581C8 - spawn_drop_burst

## Purpose
Emits five type-18 drops plus one type-3 drop and plays sound 5 (death/impact debris scatter)

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- 5-iter spawn_drop(x,y-0x1000,z,a3=75,stack=18); then spawn_drop(x,y,z,a3=77,type=3); play_sound(5,obj)

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
