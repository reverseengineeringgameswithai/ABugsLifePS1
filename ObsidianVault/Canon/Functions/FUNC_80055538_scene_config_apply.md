---
kind: function
id: FUNC_80055538
aliases:
- FUNC_80055538
- '0x80055538'
- scene_config_apply
address: '0x80055538'
name: scene_config_apply
status: byte_matched
confidence: confirmed
source_state: original_game
tier: inferred
calls:
- cd_mix_shim
- set_draw_env_offset
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch01.json
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch01.json
- src/main/80055538_scene_config_apply.c
patch_policy: safe_to_read
---

# FUNC_80055538 - scene_config_apply

## Purpose
Applies a scene descriptor struct into resident config globals and kicks CD mix setup

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- caller scene_flow_dispatcher; callees cd_mix_shim, sub_8003f4d4
- unpacks struct a0 into resident globals (byte0->0x800A6560, halfwords 24/26->set_draw_env_offset), bytes 22/23 index tables feeding cd_mix_shim, copies 19 bytes + 64 5-byte records

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
