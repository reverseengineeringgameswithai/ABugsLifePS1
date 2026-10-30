---
kind: function
id: FUNC_800661EC
aliases:
- FUNC_800661EC
- '0x800661ec'
- file_dev_dir_hook_install_and_firstfile
address: '0x800661ec'
name: file_dev_dir_hook_install_and_firstfile
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- firstfile
- strcmp
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch04_lib.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch04_lib.json
patch_policy: safe_to_read
---

# FUNC_800661EC - file_dev_dir_hook_install_and_firstfile

## Purpose
BIOS file-device dir helper: intercepts a device's dir fn (saving original + installing trampoline) and invokes firstfile

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- copies filename into 0x80086a68 (stop at ';'), scans 80-byte kernel file-CB table via strcmp
- saves matched fnptr+52 to 0x80086a60, installs trampoline 0x80066388, jal firstfile

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch04_lib.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
