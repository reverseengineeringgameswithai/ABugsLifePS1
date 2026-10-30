---
kind: function
id: FUNC_80058154
aliases:
- FUNC_80058154
- '0x80058154'
- spawn_drop_burst_type76
address: '0x80058154'
name: spawn_drop_burst_type76
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
- src/main/80058154_spawn_drop_burst_type76.c
patch_policy: safe_to_read
---

# FUNC_80058154 - spawn_drop_burst_type76

## Purpose
Emits 5 type-76 drops at the object position then plays sound 5

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- 5-iter spawn_drop(position s0[0..2], a3=76, stack=2); then play_sound(5,s0)

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
