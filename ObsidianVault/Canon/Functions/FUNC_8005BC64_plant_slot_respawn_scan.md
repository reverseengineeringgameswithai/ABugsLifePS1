---
kind: function
id: FUNC_8005BC64
aliases:
- FUNC_8005BC64
- '0x8005bc64'
- plant_slot_respawn_scan
address: '0x8005bc64'
name: plant_slot_respawn_scan
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- memset
- plant_spawn
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch01.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch01.json
patch_policy: safe_to_read
---

# FUNC_8005BC64 - plant_slot_respawn_scan

## Purpose
Scans the 64 object slots and re-spawns type-11 (plant) entries via plant_spawn

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- caller gameplay_state_reset_cursor_seed; callees memset, plant_spawn
- memset(0x80090BF0,0,960); loops 64 slots stride 132 at 0x800A9D80; type==11 and (hw+0x5C&0x120)==0x120 -> adjust field+8, plant_spawn(slot)

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
