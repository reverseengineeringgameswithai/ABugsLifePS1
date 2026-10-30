---
kind: function
id: FUNC_80050EA8
aliases:
- FUNC_80050EA8
- '0x80050ea8'
- pickup_target_reset_on_finalize
address: '0x80050ea8'
name: pickup_target_reset_on_finalize
status: byte_matched
confidence: confirmed
source_state: original_game
tier: inferred
calls:
- nearest_pickup_finalize
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch02.json
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch02.json
- src/main/80050ea8_pickup_target_reset_on_finalize.c
patch_policy: safe_to_read
---

# FUNC_80050EA8 - pickup_target_reset_on_finalize

## Purpose
Resets the two pickup-target globals when nearest_pickup_finalize reports the target invalid

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- early-out a0==0; nearest_pickup_finalize(a0+4); if 0 -> sh 0,[0x8008229c], sw 0,[0x80082370]

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
