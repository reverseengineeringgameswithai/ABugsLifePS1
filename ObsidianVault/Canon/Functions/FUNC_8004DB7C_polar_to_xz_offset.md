---
kind: function
id: FUNC_8004DB7C
aliases:
- FUNC_8004DB7C
- '0x8004db7c'
- polar_to_xz_offset
address: '0x8004db7c'
name: polar_to_xz_offset
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls: []
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch02.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch02.json
patch_policy: safe_to_read
---

# FUNC_8004DB7C - polar_to_xz_offset

## Purpose
Polar-to-Cartesian: offsets a base X/Z by sin/cos of angle a0 * distance a1 into X/Z globals

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- trig table 0x80074970: sine at (a0&0xfff)<<1, cosine at (a0+1024)&0xfff; * magnitude a1 >>9
- adds sine to [0x80090bcc]->[0x80090bd8], subtracts cosine from [0x80090bf4]->[0x80090c00]

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
