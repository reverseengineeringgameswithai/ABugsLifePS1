---
kind: function
id: FUNC_8003EEC8
aliases:
- FUNC_8003EEC8
- '0x8003eec8'
- dat_load_256byte_table
address: '0x8003eec8'
name: dat_load_256byte_table
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- memset
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch01.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch01.json
patch_policy: safe_to_read
---

# FUNC_8003EEC8 - dat_load_256byte_table

## Purpose
Loads or 0xFF-clears a 256-byte lookup table at 0x800901C8 during DAT parsing

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- caller dat_parser_relocator; only callee memset
- a0==0: memset(0x800901C8,0xFF,256), gp+1236=-1; else lwl/lwr copy 256B from [0x80089c9c]+24 into 0x800901C8, clears gp+1236/1240

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
