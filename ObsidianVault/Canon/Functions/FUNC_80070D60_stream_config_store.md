---
kind: function
id: FUNC_80070D60
aliases:
- FUNC_80070D60
- '0x80070d60'
- stream_config_store
address: '0x80070d60'
name: stream_config_store
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
- src/main/80070d60_stream_config_store.c
patch_policy: safe_to_read
---

# FUNC_80070D60 - stream_config_store

## Purpose
Stashes three streaming-config arguments into globals for StSetStream

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- caller StSetStream (libpress); leaf
- stores a0->0x800B0D08, a1->0x8009538C, a2->0x800B0CC0; 32-byte setter

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
