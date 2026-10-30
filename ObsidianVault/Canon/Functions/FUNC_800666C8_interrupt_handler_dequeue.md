---
kind: function
id: FUNC_800666C8
aliases:
- FUNC_800666C8
- '0x800666c8'
- interrupt_handler_dequeue
address: '0x800666c8'
name: interrupt_handler_dequeue
status: byte_matched
confidence: confirmed
source_state: original_game
tier: inferred
calls:
- EnterCriticalSection
- ExitCriticalSection
- SysDeqIntRP
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch01.json
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch01.json
- src/main/800666c8_interrupt_handler_dequeue.c
patch_policy: safe_to_read
---

# FUNC_800666C8 - interrupt_handler_dequeue

## Purpose
Removes an interrupt-priority-chain handler in a critical section (SysDeqIntRP)

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- EnterCriticalSection -> SysDeqIntRP(priority=1, cb=0x80086A90) -> ExitCriticalSection, returns 1
- sole caller sub_80066618

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
