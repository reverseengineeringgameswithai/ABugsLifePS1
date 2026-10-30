---
kind: function
id: FUNC_8003F2F0
aliases:
- FUNC_8003F2F0
- '0x8003f2f0'
- wait_for_frame_sync_flag
address: '0x8003f2f0'
name: wait_for_frame_sync_flag
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- EnterCriticalSection
- ExitCriticalSection
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch01.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch01.json
patch_policy: safe_to_read
---

# FUNC_8003F2F0 - wait_for_frame_sync_flag

## Purpose
Drains a queued counter then blocks on an interrupt-cleared sync flag (frame/vblank sync)

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- EnterCriticalSection/ExitCriticalSection bracket
- drains counter gp+1696, zeroes it; sets 0x80082250=1 and busy-spins until an ISR clears it
- callers gameplay_state_reset_cursor_seed, level_transition_orchestrator, sub_8005b440, sub_8005b4ec

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
