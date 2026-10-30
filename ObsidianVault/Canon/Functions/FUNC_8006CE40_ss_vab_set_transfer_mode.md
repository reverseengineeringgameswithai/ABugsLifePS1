---
kind: function
id: FUNC_8006CE40
aliases:
- FUNC_8006CE40
- '0x8006ce40'
- ss_vab_set_transfer_mode
address: '0x8006ce40'
name: ss_vab_set_transfer_mode
status: byte_matched
confidence: confirmed
source_state: original_game
tier: inferred
calls: []
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch01.json
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch01.json
- src/main/8006ce40_ss_vab_set_transfer_mode.c
patch_policy: safe_to_read
---

# FUNC_8006CE40 - ss_vab_set_transfer_mode

## Purpose
libsnd internal: sets a VAB/SPU transfer-mode flag from the arg

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- Sets 0x800814F8 to 0 when a0==1 else 1; 44-byte leaf
- callers SsVabOpenHeadWithMode, SsVabTransBody, _SsVmInit (libsnd)

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
