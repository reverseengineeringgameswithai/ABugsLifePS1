---
kind: function
id: LEGACY_FUNC_80049C30_mover_init_from_record
aliases:
- LEGACY_FUNC_80049C30_mover_init_from_record
- mover_init_from_record
address: '0x80049c30'
name: mover_init_from_record
status: superseded
canonical_address: false
superseded_by: FUNC_80049C30_enemy_reinstantiate_from_spawn
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

# FUNC_80049C30 - mover_init_from_record

## Purpose
Initializes a mover actor instance from its LEVEL.DAT source record

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- Reads source record ptr obj[+0x80]; copies record XYZ (word<<5) to obj+4/8/12 and prev-pos obj+40/44/48
- byte13<<2 indexes descriptor table 0x80077af8 -> obj+112; zeroes velocity obj+16..36
- callers mover_updater, sub_8004a42c

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
