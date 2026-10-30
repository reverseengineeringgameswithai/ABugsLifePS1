---
kind: function
id: FUNC_80043144
aliases:
- FUNC_80043144
- '0x80043144'
- find_free_slot_16entry
address: '0x80043144'
name: find_free_slot_16entry
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
- src/main/80043144_find_free_slot_16entry.c
patch_policy: safe_to_read
---

# FUNC_80043144 - find_free_slot_16entry

## Purpose
Scans a 16-entry stride-12 table for the first record whose halfword is -1 (free-slot allocator lookup)

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- loop v1 0..16, lh[0x8009165a + a0] (a0 +=12 stride), returns index when field==-1 else -1

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
