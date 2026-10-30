---
kind: function
id: FUNC_8006BABC
aliases:
- FUNC_8006BABC
- '0x8006babc'
- spu_fwrite_by_io_body
address: '0x8006babc'
name: spu_fwrite_by_io_body
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- _spu_Fw1ts
- printf
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch04_lib.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch04_lib.json
patch_policy: safe_to_read
---

# FUNC_8006BABC - spu_fwrite_by_io_body

## Purpose
Body of _spu_FwriteByIO: programmed-IO (non-DMA) block write to SPU RAM

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- _spu_FwriteByIO @0x8006baac loads SPU IO base, falls through; body writes halfwords via SPU IO regs +424/+426, calls _spu_Fw1ts, printf on timeout

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch04_lib.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
