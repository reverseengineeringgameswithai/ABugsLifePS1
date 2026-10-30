---
kind: function
id: FUNC_8005F7F8
aliases:
- FUNC_8005F7F8
- '0x8005f7f8'
- vsprintf_core
address: '0x8005f7f8'
name: vsprintf_core
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- memchr
- memmove
- strlen
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch02.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch02.json
patch_policy: safe_to_read
---

# FUNC_8005F7F8 - vsprintf_core

## Purpose
Core printf/vsprintf-style format-and-output routine (buffer a0, format a1)

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- scans format a1 for % and flags -/+/space/0/#; strlen/memmove/memchr place+pad fields into buffer a0
- 2128B printf-family conversion loop

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
