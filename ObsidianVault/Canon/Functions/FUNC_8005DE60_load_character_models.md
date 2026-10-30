---
kind: function
id: FUNC_8005DE60
aliases:
- FUNC_8005DE60
- '0x8005de60'
- load_character_models
address: '0x8005de60'
name: load_character_models
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- collect_object_short_list
- level_chunk_loader
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch02.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch02.json
patch_policy: safe_to_read
---

# FUNC_8005DE60 - load_character_models

## Purpose
Dispatcher that registers/loads up to 64 character models by (path,id) and drives the level chunk loader

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- jump-table cases set a0=path string, a3=incrementing id (13,14,15..) then common tail 0x8005e274
- strings = 'chars\wasp','chars2\dot','chars2\grassh','chars2\thumper'... from 0x8001b94c; tail loops 64 stride-132 records, calls level_chunk_loader

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Runtime-confirmed and fully decoded (E05, 2026-08-03)

The inferred role is now proven and precise. `0x8005DE60` is a label inside
`level_load_chunks` (0x8005DAD0): the "64 stride-132 loop" is the walk of the
actor pool `0x8009FD80` itself, dispatching each record id (1..41) through jr
table 0x8001BBDC; the case bodies at 0x8005DE64+ are the character-model loads
(a3 == actor id). Loaded pointers persist at **0x800A6300 + 4*id**
(first-load-guarded in `level_chunk_loader` 0x8005D654). The complete id→path
table (EXE-decoded, zero inconsistencies) and 16-level live confirmation:
[[SYS_actor_model_loading]], `analysis/phase4_e05_model_binding_static.json`,
`analysis/phase4_e05_model_pointers_live.json`. Note: the old evidence line's
"strings from 0x8001b94c" narrows to the pool at 0x8001B87C+ (Flik variants)
and 0x8001B8B8+ (per-id paths).

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]] · [[SYS_actor_model_loading]] · [[EXP_2026-08-03_phase4_e05_actor_model_binding]]
