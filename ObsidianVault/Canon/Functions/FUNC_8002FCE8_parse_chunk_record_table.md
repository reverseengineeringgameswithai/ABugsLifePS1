---
kind: function
id: FUNC_8002FCE8
aliases:
- FUNC_8002FCE8
- '0x8002fce8'
- parse_chunk_record_table
address: '0x8002fce8'
name: parse_chunk_record_table
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

# FUNC_8002FCE8 - parse_chunk_record_table

## Purpose
Parses a count-prefixed 76-byte record stream into an 84-byte resident array with pointer relocation

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- callers level_chunk_loader, load_named_file
- a1 = pointer-cursor into a count-prefixed stream; iterates 76-byte records, filters field+0x14<256, copies words +8/12/16/20 + halfwords into 84-byte-stride array 0x8009xxxx
- handles 0x12345678 relocation placeholder via pointer table; returns count

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
