---
kind: function
id: FUNC_80039BD8
aliases:
- FUNC_80039BD8
- '0x80039bd8'
- pad_rumble_update
address: '0x80039bd8'
name: pad_rumble_update
status: byte_matched
confidence: confirmed
source_state: original_game
tier: inferred
calls:
- PadSetAct
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch01.json
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch01.json
- src/main/80039bd8_pad_rumble_update.c
patch_policy: safe_to_read
---

# FUNC_80039BD8 - pad_rumble_update

## Purpose
Sets controller vibration via PadSetAct only when the requested motor state changed

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- splits arg0 into bit0 (small motor) and &0xfe (large motor); compares last-state 0x800a5cba/0x800a5cbb, early-out if unchanged
- on change writes state + PadSetAct(0,table,2)
- callers gameplay_frame_render, scene_flow_dispatcher, sfx_voice_trigger_gl_glue

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
