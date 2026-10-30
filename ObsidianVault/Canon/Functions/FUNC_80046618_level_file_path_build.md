---
kind: function
id: FUNC_80046618
aliases:
- FUNC_80046618
- '0x80046618'
- level_file_path_build
address: '0x80046618'
name: level_file_path_build
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

# FUNC_80046618 - level_file_path_build

## Purpose
Constructs a level chunk filename/path with numeric index and mode-selected suffix

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- Caller collision_grid_level_load_chu_glue; callee strcat
- Builds a string from template 0x80082260/0x80082268, formats index a0 as decimal via /10, appends digit chars + backslash, strcat-selects suffix by a2

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
