---
kind: function
id: FUNC_8005D924
aliases:
- FUNC_8005D924
- '0x8005d924'
- level_chunk_file_load
address: '0x8005d924'
name: level_chunk_file_load
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- load_named_file
- parse_chunk_record_table
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch01.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch01.json
patch_policy: safe_to_read
---

# FUNC_8005D924 - level_chunk_file_load

## Purpose
Loads a named level chunk file into the streaming buffer, records handle/offset

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- Caller level_load_chunks; callees load_named_file and sub_8002fce8
- Indexes table 0x800a6300 by a3, sets gp+1448=1, stores handle 0x80082340, advances offset *s0, validates chunk id==9

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
