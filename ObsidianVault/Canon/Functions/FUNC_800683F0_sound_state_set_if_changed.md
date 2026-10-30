---
kind: function
id: FUNC_800683F0
aliases:
- FUNC_800683F0
- '0x800683f0'
- sound_state_set_if_changed
address: '0x800683f0'
name: sound_state_set_if_changed
status: byte_matched
confidence: confirmed
source_state: original_game
tier: inferred
calls: []
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch01.json
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch01.json
- src/main/800683f0_sound_state_set_if_changed.c
patch_policy: safe_to_read
---

# FUNC_800683F0 - sound_state_set_if_changed

## Purpose
Conditionally updates a sound-subsystem global only when the arg differs

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- Caller sound_system_init
- Reads global 0x80080eb8; if a0==current returns; else stores a0 to 0x80080eb8

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
