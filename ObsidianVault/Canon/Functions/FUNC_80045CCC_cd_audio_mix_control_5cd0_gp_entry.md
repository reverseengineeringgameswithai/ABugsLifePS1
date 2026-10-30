---
kind: function
id: FUNC_80045CCC
aliases:
- FUNC_80045CCC
- '0x80045ccc'
- cd_audio_mix_control_5cd0_gp_entry
address: '0x80045ccc'
name: cd_audio_mix_control_5cd0_gp_entry
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

# FUNC_80045CCC - cd_audio_mix_control_5cd0_gp_entry

## Purpose
Alternate entry preloading v0=gp+1064 before cd_audio_mix_control_5cd0

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- single lw v0,1064(gp), no return; falls into cd_audio_mix_control_5cd0 (0x80045cd0)

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch06_residual.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
