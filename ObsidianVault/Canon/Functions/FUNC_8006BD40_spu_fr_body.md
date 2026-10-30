---
kind: function
id: FUNC_8006BD40
aliases:
- FUNC_8006BD40
- '0x8006bd40'
- spu_fr_body
address: '0x8006bd40'
name: spu_fr_body
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- _spu_FsetDelayR
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

# FUNC_8006BD40 - spu_fr_body

## Purpose
Body of _spu_Fr_: programs and kicks an SPU DMA transfer

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- _spu_Fr_ @0x8006bd38 loads SPU IO base, falls through; body sets SPU transfer-addr/ctrl regs, OR 0x30 into +426, sets busy flag, calls _spu_FsetDelayR/_spu_Fw1ts

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch04_lib.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
