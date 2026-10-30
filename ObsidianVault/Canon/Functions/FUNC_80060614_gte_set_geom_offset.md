---
kind: function
id: FUNC_80060614
aliases:
- FUNC_80060614
- '0x80060614'
- gte_set_geom_offset
address: '0x80060614'
name: gte_set_geom_offset
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls: []
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch01.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch01.json
patch_policy: safe_to_read
---

# FUNC_80060614 - gte_set_geom_offset

## Purpose
Sets the GTE screen offset registers OFX/OFY (SetGeomOffset equivalent)

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- CTC2 writes arg0<<16 to GTE ctrl reg 24 (OFX), arg1<<16 to reg 25 (OFY) — .word 0x48c4c000/0x48c5c800
- <<16 fixed-point = SetGeomOffset format
- caller boot_subsystem_init

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
