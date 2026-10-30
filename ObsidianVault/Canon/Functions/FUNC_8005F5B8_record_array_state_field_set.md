---
kind: function
id: FUNC_8005F5B8
aliases:
- FUNC_8005F5B8
- '0x8005f5b8'
- record_array_state_field_set
address: '0x8005f5b8'
name: record_array_state_field_set
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

# FUNC_8005F5B8 - record_array_state_field_set

## Purpose
Sets the +0x32 state halfword across a range of the 84-byte record array keyed off a sound/voice slot

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- caller sfx_play_sound_glue; leaf
- a0[0] indexes 0x800A6300, field+4 *84 -> 84-byte record array; loop1 sets hw+0x32=1 for records 0..19 (skip 4,7); loop2 +0x32=2 for 26..28

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
