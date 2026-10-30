---
kind: function
id: FUNC_80052090
aliases:
- FUNC_80052090
- '0x80052090'
- collect_object_short_list
address: '0x80052090'
name: collect_object_short_list
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls: []
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch01.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch01.json
patch_policy: safe_to_read
---

# FUNC_80052090 - collect_object_short_list

## Purpose
Builds a -1-terminated int16 token list filtered from the object table plus a jump-table pass

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- writes header 5, scans 64 object slots 0x800a9d80 stride 0x84 (type==11 + subflags), appends shorts from 0x80082044
- second pass over count-list stride 16, jump-table 0x8001b2dc on byte+12; terminates -1
- caller sub_8005de60

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
