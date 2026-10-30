---
kind: function
id: FUNC_80057F4C
aliases:
- FUNC_80057F4C
- '0x80057f4c'
- spawn_drop_burst_8
address: '0x80057f4c'
name: spawn_drop_burst_8
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

# FUNC_80057F4C - spawn_drop_burst_8

## Purpose
Emits a burst of 8 drops from an object's position (type per object) plus a positional sound

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- 8-iter spawn_drop using object fields [+102],[+8],[+4],[+12]; type from table by object nibble
- then player_x/y/z + trig, sfx_proximity_priority_gate, play_sound

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
