---
kind: function
id: FUNC_80046538
aliases:
- FUNC_80046538
- '0x80046538'
- build_level_asset_path
address: '0x80046538'
name: build_level_asset_path
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- strcat
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch01.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch01.json
patch_policy: safe_to_read
---

# FUNC_80046538 - build_level_asset_path

## Purpose
Builds a per-level directory-prefixed asset path 'levelNN\<suffix>'

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- index<10: 'level0'+'0'+idx -> level0N; >=10: 'level'+tens/ones -> levelNN; writes '\\'+NUL, strcat(arg2 suffix)
- callers collision_grid_builder, collision_grid_level_load_chu_glue, resource_id_dat_load_dispatcher

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
