---
kind: function
id: FUNC_80038EE8
aliases:
- FUNC_80038EE8
- '0x80038ee8'
- object_slot_clear_field
address: '0x80038ee8'
name: object_slot_clear_field
status: byte_matched
confidence: confirmed
source_state: original_game
tier: inferred
calls: []
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch05_final.json
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch05_final.json
- src/main/80038ee8_object_slot_clear_field.c
patch_policy: safe_to_read
---

# FUNC_80038EE8 - object_slot_clear_field

## Purpose
Maps an index through a handle table to a 0x30-byte record and zeroes its first halfword

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- id table 0x800a2080 by a0*2 -> handle; if !=0, handle*48 stride, sh 0 to 0x800a7e74+handle*48
- sibling of object_slot_set_field_6 (writes 0 vs 6)

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch05_final.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
