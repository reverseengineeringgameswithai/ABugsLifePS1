---
kind: function
id: FUNC_800653DC
aliases:
- FUNC_800653DC
- '0x800653dc'
- ResetCallback_dispatch_tail
address: '0x800653dc'
name: ResetCallback_dispatch_tail
status: byte_matched
confidence: confirmed
source_state: original_game
tier: inferred
calls: []
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch04_lib.json
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch04_lib.json
- src/main/800653dc_ResetCallback_dispatch_tail.c
patch_policy: safe_to_read
---

# FUNC_800653DC - ResetCallback_dispatch_tail

## Purpose
Tail/body of libapi ResetCallback; invokes kernel callback-table slot +0xC

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- ResetCallback @0x800653d4 (8B) loads kernel dispatch-table ptr 0x80080de0 and falls through
- body: lw v0,12(v0); jalr v0 — calls table entry +0xC

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch04_lib.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
