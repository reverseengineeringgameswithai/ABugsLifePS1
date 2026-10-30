---
kind: function
id: FUNC_8004574C
aliases:
- FUNC_8004574C
- '0x8004574c'
- build_prefixed_filename
address: '0x8004574c'
name: build_prefixed_filename
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- strcat
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch02.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch02.json
patch_policy: safe_to_read
---

# FUNC_8004574C - build_prefixed_filename

## Purpose
Assembles a string = 2-char gp code + caller name + constant suffix (filename/path builder)

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- writes 2 bytes from gp+1088/1089 to buffer 0x8009B668, strcat(a0), strcat(const 0x800821DC); returns buffer

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
