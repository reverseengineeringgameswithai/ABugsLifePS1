---
kind: function
id: FUNC_80066618
aliases:
- FUNC_80066618
- '0x80066618'
- pad_subsystem_shutdown
address: '0x80066618'
name: pad_subsystem_shutdown
status: byte_matched
confidence: confirmed
source_state: original_game
tier: inferred
calls:
- StopPAD2
- interrupt_handler_dequeue
- pad_stop_driver_thunk
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch04_lib.json
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch04_lib.json
- src/main/80066618_pad_subsystem_shutdown.c
patch_policy: safe_to_read
---

# FUNC_80066618 - pad_subsystem_shutdown

## Purpose
PAD subsystem teardown: stops PAD2, unhooks its interrupt handler, clears the init flag

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- calls sub_80066820, StopPAD2, interrupt_handler_dequeue; then clears PAD-init flag 0x80080e68

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch04_lib.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
