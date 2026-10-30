---
kind: function
id: FUNC_8006BC80
aliases:
- FUNC_8006BC80
- '0x8006bc80'
- spu_fidma_body
address: '0x8006bc80'
name: spu_fidma_body
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- DeliverEvent
- _spu_Fw1ts
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch04_lib.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch04_lib.json
patch_policy: safe_to_read
---

# FUNC_8006BC80 - spu_fidma_body

## Purpose
Body of _spu_FiDMA: SPU DMA-completion interrupt handler

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- _spu_FiDMA @0x8006bc78 loads SPU IO base, falls through; body polls SPU ctrl +426 DMA bits, calls user callback or DeliverEvent(0xf0000009,0x20)

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch04_lib.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
