---
kind: function
id: FUNC_8006BDF4
aliases:
- FUNC_8006BDF4
- '0x8006bdf4'
- spu_transfer_mode_dispatch_body
address: '0x8006bdf4'
name: spu_transfer_mode_dispatch_body
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- _spu_FsetDelayR
- _spu_FsetDelayW
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch04_lib.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch04_lib.json
patch_policy: safe_to_read
---

# FUNC_8006BDF4 - spu_transfer_mode_dispatch_body

## Purpose
Body of _spu_t: core SPU transfer mode dispatcher (address/mode/kick)

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- _spu_t @0x8006bde4 loads SPU IO base, falls through; body switch on mode 0/1/2/3 selecting SPU transfer setup, calls _spu_FsetDelayR/W

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch04_lib.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
