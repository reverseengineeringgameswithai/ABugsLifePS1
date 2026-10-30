---
kind: function
id: FUNC_8004A20C
aliases:
- FUNC_8004A20C
- '0x8004a20c'
- play_object_sound_42
address: '0x8004a20c'
name: play_object_sound_42
status: byte_matched
confidence: confirmed
source_state: original_game
tier: inferred
calls:
- play_sound
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch02.json
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch02.json
- src/main/8004a20c_play_object_sound_42.c
patch_policy: safe_to_read
---

# FUNC_8004A20C - play_object_sound_42

## Purpose
Wrapper firing sound id 42 using the object's referenced position/parameter block

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- a1=[a0+4]+4; play_sound(a0=42, a1)

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
