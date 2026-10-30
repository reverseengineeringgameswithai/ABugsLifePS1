---
kind: function
id: FUNC_8004A0A0
aliases:
- FUNC_8004A0A0
- '0x8004a0a0'
- object_play_sound_38_type_1_10
address: '0x8004a0a0'
name: object_play_sound_38_type_1_10
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- play_sound
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch02.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch02.json
patch_policy: safe_to_read
---

# FUNC_8004A0A0 - object_play_sound_38_type_1_10

## Purpose
Plays sound 38 for objects of type 1 or 10 when the linked sub-struct +0x44 flag is clear

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- a1=[a0+4], gate [a1+68]!=0 skip; check lh[a0]==1||==10; play_sound(38,a1+4)

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
