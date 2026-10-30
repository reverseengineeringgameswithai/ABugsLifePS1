---
kind: function
id: FUNC_80066388
aliases:
- FUNC_80066388
- '0x80066388'
- file_dev_dir_hook_trampoline
address: '0x80066388'
name: file_dev_dir_hook_trampoline
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
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

# FUNC_80066388 - file_dev_dir_hook_trampoline

## Purpose
Trampoline installed by 0x800661ec: restores the original file-device dir fn and forwards the call

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- one-shot init flag on *a0; scans file-CB table, restores saved fnptr 0x80086a60 into record+52; tail-calls original(a0,a1,a2)

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch04_lib.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
