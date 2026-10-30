---
kind: function
id: FUNC_80055D4C
aliases:
- FUNC_80055D4C
- '0x80055d4c'
- load_numbered_asset_file
address: '0x80055d4c'
name: load_numbered_asset_file
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- universal_file_loader
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch02.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch02.json
patch_policy: safe_to_read
---

# FUNC_80055D4C - load_numbered_asset_file

## Purpose
Formats a two-digit index into a filename and loads the asset

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- formats a1 as two decimal ASCII digits into a filename template; a1=0x80095398 buf; jal universal_file_loader

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
