---
kind: function
id: FUNC_80067FB0
aliases:
- FUNC_80067FB0
- '0x80067fb0'
- seq_playback_state_init
address: '0x80067fb0'
name: seq_playback_state_init
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- _SsVmSeqKeyOff
- clear_global_short_80091610
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch01.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch01.json
patch_policy: safe_to_read
---

# FUNC_80067FB0 - seq_playback_state_init

## Purpose
Initializes/resets a SEQ sequence playback structure (16 channels, key-off, default vols)

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- callers SsSeqCalledTbyT (SEQ tick), sub_80068134/815c; indexes SEQ table 0x800b01a0 by arg0
- clears status bits, calls _SsVmSeqKeyOff, inits 16 channels (pan 64, vol 127), master vols 127

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
