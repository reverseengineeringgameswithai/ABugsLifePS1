---
kind: function
id: FUNC_80027C60
aliases:
- FUNC_80027C60
- '0x80027c60'
- gp_flags_and_buffers_clear
address: '0x80027c60'
name: gp_flags_and_buffers_clear
status: byte_matched
confidence: confirmed
source_state: original_game
tier: inferred
calls:
- memset
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch01.json
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch01.json
- src/main/80027c60_gp_flags_and_buffers_clear.c
patch_policy: safe_to_read
---

# FUNC_80027C60 - gp_flags_and_buffers_clear

## Purpose
Resets a group of gp flag globals and memsets two fixed buffers to zero

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- Zeroes 7 gp-relative halfword flags: sh $zero at gp+1196,1228,1324,1584,1840,1616,1864
- Calls memset (jal 0x8005f7ac) twice: buffer 0x800b0230 size 128, buffer 0x8009b3a8 size 512
- No return value; pure state-clear routine

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
