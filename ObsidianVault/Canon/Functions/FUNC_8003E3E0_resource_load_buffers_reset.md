---
kind: function
id: FUNC_8003E3E0
aliases:
- FUNC_8003E3E0
- '0x8003e3e0'
- resource_load_buffers_reset
address: '0x8003e3e0'
name: resource_load_buffers_reset
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- gp_flags_and_buffers_clear
- memset
- reset_visual_sprite_object_pool
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch01.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch01.json
patch_policy: safe_to_read
---

# FUNC_8003E3E0 - resource_load_buffers_reset

## Purpose
Clears subsystem buffers/globals during resource(DAT) load

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- Five memset calls clearing 0x80096da0(256),0x80090358(25200),0x800a7e48(0x8340),scratchpad 0x1f800000 twice(1024)
- Fills 256B table 0x800a7b47 with 128, sets gp+1028/960/964 to -1, zeroes 0x8008xxxx globals
- sole caller resource_id_dat_load_dispatcher; calls sub_80027c60,sub_8003f5fc

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
