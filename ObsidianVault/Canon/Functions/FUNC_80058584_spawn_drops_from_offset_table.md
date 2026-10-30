---
kind: function
id: FUNC_80058584
aliases:
- FUNC_80058584
- '0x80058584'
- spawn_drops_from_offset_table
address: '0x80058584'
name: spawn_drops_from_offset_table
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- spawn_drop
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch02.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch02.json
patch_policy: safe_to_read
---

# FUNC_80058584 - spawn_drops_from_offset_table

## Purpose
Spawns 3 drops offset from a base by dx/dz pairs from a global offset-table pointer

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- loop 3x reading global byte-stream 0x800822f4 (2 bytes/iter), pair<<3 added to base x/z, spawn_drop

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
