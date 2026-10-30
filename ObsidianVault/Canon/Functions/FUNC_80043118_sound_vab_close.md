---
kind: function
id: FUNC_80043118
aliases:
- FUNC_80043118
- '0x80043118'
- sound_vab_close
address: '0x80043118'
name: sound_vab_close
status: byte_matched
confidence: confirmed
source_state: original_game
tier: inferred
calls:
- SsVabClose
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch02.json
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch02.json
- src/main/80043118_sound_vab_close.c
patch_policy: safe_to_read
---

# FUNC_80043118 - sound_vab_close

## Purpose
Closes a SPU VAB and invalidates its stored id

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- if a0>=0 calls SsVabClose 0x8006b0ac; then sh -1 to gp+1040 (VAB-id slot)

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
