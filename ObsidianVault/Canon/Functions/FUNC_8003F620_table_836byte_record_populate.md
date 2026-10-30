---
kind: function
id: FUNC_8003F620
aliases:
- FUNC_8003F620
- '0x8003f620'
- table_836byte_record_populate
address: '0x8003f620'
name: table_836byte_record_populate
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

# FUNC_8003F620 - table_836byte_record_populate

## Purpose
Populates one fixed-stride (836-byte) record in a large global table from caller vectors

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- record index = a0*836; writes halfwords/bytes and copies 16-byte vector blocks from a3,t0 into table based at 0x800a...
- single caller sub_80042c70

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
