---
kind: function
id: FUNC_80057DD4
aliases:
- FUNC_80057DD4
- '0x80057dd4'
- spawn_drop_burst_by_object_type
address: '0x80057dd4'
name: spawn_drop_burst_by_object_type
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- play_sound
- sfx_proximity_priority_gate
- spawn_drop
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch02.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch02.json
patch_policy: safe_to_read
---

# FUNC_80057DD4 - spawn_drop_burst_by_object_type

## Purpose
16-drop scatter burst whose type is selected from a per-object-type table, plus positional SFX and sound

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- 16-iter spawn_drop(coords [s1+4],[s1+8]+[s1+102],[s1+12], type=base+parity)
- base type from table 0x8007a0b8[objtype&0xf]; sfx_proximity_priority_gate a3 from 0x8007a0c8; play_sound(4,s1+4)

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
