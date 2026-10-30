---
kind: function
id: FUNC_80061678
aliases:
- FUNC_80061678
- '0x80061678'
- text_stream_printf
address: '0x80061678'
name: text_stream_printf
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
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

# FUNC_80061678 - text_stream_printf

## Purpose
printf-family formatter appending formatted bytes into a bounded text-stream buffer struct

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- parses format string (s3), handles % and %%; writes into stream struct buf s1+0x24 cursor s1+0x28 cap s1+0x1c
- /10 reciprocal 0xcccccccd for decimal; callee strlen

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
