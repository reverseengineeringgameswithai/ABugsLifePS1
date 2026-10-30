---
kind: function
id: FUNC_80045704
aliases:
- FUNC_80045704
- '0x80045704'
- string_to_upper
address: '0x80045704'
name: string_to_upper
status: byte_matched
confidence: confirmed
source_state: original_game
tier: inferred
calls: []
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch02.json
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch02.json
- src/main/80045704_string_to_upper.c
patch_policy: safe_to_read
---

# FUNC_80045704 - string_to_upper

## Purpose
In-place strupr: lowercase->uppercase, other bytes unchanged

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- loops NUL-terminated string at a0; per byte range 'a'..'z' -> subtract 32, store back

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
