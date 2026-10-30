---
kind: function
id: FUNC_80030D64
aliases:
- FUNC_80030D64
- '0x80030d64'
- all_model_file_load_unpack
address: '0x80030d64'
name: all_model_file_load_unpack
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- strcat
- strcpy
- universal_file_loader
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch01.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch01.json
patch_policy: safe_to_read
---

# FUNC_80030D64 - all_model_file_load_unpack

## Purpose
Loads a <name>.ALL model/instance file and unpacks stride-0x30 records with XYZ<<5 scaling

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- strcpy(buf,arg0)+strcat(buf,'.all' @0x80082130)+universal_file_loader(buf,*arg2)
- first-load guard gp+1316, stashes ptr to *arg2
- unpacks stride-0x30 records, scales XYZ lanes <<5 at +0/4/8
- caller collision_grid_builder

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
