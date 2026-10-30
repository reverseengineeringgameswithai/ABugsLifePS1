---
kind: function
id: FUNC_80057920
aliases:
- FUNC_80057920
- '0x80057920'
- spawn_object_burst_ring
address: '0x80057920'
name: spawn_object_burst_ring
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- contact_object_spawn_full
- play_sound
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch01.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch01.json
patch_policy: safe_to_read
---

# FUNC_80057920 - spawn_object_burst_ring

## Purpose
Spawns a ring/burst of 8 objects from a parameter table and plays a sound

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- Caller sub_8004c5e4; callees contact_object_spawn_full and play_sound(20)
- Loops 8x reading angle/param table 0x80074970 (stride 1024), spawns object per iter, writes -3072 to s2+32, plays sound

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
