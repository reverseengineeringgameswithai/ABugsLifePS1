---
kind: function
id: FUNC_80058620
aliases:
- FUNC_80058620
- '0x80058620'
- spawn_drop_burst_type4
address: '0x80058620'
name: spawn_drop_burst_type4
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
- src/main/80058620_spawn_drop_burst_type4.c
patch_policy: safe_to_read
---

# FUNC_80058620 - spawn_drop_burst_type4

## Purpose
Emits 5 type-4 drops with proximity SFX then plays sound 6

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- 5-iter spawn_drop(actor xyz, type=4, a3=(s0&1)|6); sfx_proximity_priority_gate(...,16); play_sound(6,actor)
- sibling of 0x800580e0

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
