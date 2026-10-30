---
kind: function
id: FUNC_800580E0
aliases:
- FUNC_800580E0
- '0x800580e0'
- spawn_drop_burst_type2
address: '0x800580e0'
name: spawn_drop_burst_type2
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
- src/main/800580e0_spawn_drop_burst_type2.c
patch_policy: safe_to_read
---

# FUNC_800580E0 - spawn_drop_burst_type2

## Purpose
Emits 5 type-2 drops then plays sound 5 (debris burst)

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- 5-iter spawn_drop(actor xyz, type=2, a3=(s0&1)+9); then play_sound(5,actor)

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
