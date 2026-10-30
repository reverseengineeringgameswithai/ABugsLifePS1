---
kind: function
id: FUNC_8003E064
aliases:
- FUNC_8003E064
- '0x8003e064'
- draw_string_centered
address: '0x8003e064'
name: draw_string_centered
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- text_draw_stub
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch02.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch02.json
patch_policy: safe_to_read
---

# FUNC_8003E064 - draw_string_centered

## Purpose
Computes horizontal centering for a string and passes it to the text-draw primitive

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- scans string counting chars (stop NUL/CR/%), width=count*gp+1032
- X=160-width/2, tail-calls draw routine 0x8003e054(str,y,x)

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
