---
kind: function
id: FUNC_8006C07C
aliases:
- FUNC_8006C07C
- '0x8006c07c'
- spu_fw_body
address: '0x8006c07c'
name: spu_fw_body
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- _spu_FwriteByIO
- _spu_t
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch04_lib.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch04_lib.json
patch_policy: safe_to_read
---

# FUNC_8006C07C - spu_fw_body

## Purpose
Body of _spu_Fw: SPU write dispatcher choosing DMA vs programmed-IO

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- _spu_Fw @0x8006c074 loads mode flag, falls through; body flag==0 -> _spu_t(2/1/3) DMA path, else _spu_FwriteByIO IO path; returns len

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch04_lib.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
