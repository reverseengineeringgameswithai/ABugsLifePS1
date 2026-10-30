---
kind: function
id: FUNC_80055D38
aliases:
- FUNC_80055D38
- '0x80055d38'
- load_numbered_asset_file_scene_entry
address: '0x80055d38'
name: load_numbered_asset_file_scene_entry
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls: []
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch06_residual.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch06_residual.json
patch_policy: safe_to_read
---

# FUNC_80055D38 - load_numbered_asset_file_scene_entry

## Purpose
Alternate entry computing scene_id/10 before load_numbered_asset_file

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- 20B, no return; caller scene_flow_dispatcher; lw a1,0x80082504 (current_scene_id); div-by-10 magic 0x66666667; falls into load_numbered_asset_file

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch06_residual.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
