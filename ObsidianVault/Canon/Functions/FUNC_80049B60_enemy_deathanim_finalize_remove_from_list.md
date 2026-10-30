---
kind: function
id: FUNC_80049B60
aliases:
- FUNC_80049B60
- '0x80049b60'
- enemy_deathanim_finalize_remove_from_list
address: '0x80049b60'
name: enemy_deathanim_finalize_remove_from_list
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls: []
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch02.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch02.json
patch_policy: safe_to_read
---

# FUNC_80049B60 - enemy_deathanim_finalize_remove_from_list

## Purpose
Finalizes enemy death: clears state and removes actor from the damageable-object pointer table

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- shared tail 0x80049b64 of enemy_update_deathanim; sets actor+0x4a=-1, zeroes +0x6e/+0x5a
- when s1&2 scans damageable_object_ptr_table 0x80090748, compacts list
- ⚡ 2026-08-06 live-discovered and now statically enumerated by the corrected C
  writer query: the compaction stores are `0x80049C10`
  (`sw a0,0x0(v1)` — moves a live table entry down) and `0x80049C14`
  (`sw zero,0x0(v0)` — nulls the source), base `a1 = 0x80090748` materialised
  at `0x80049BF4/BF8`. These are two additional known actor-table writers — the
  pair the "exactly 4 writers" census missed (computed-base spelling).
  `0x80049C14`'s null value is proved by encoding. `0x80049C10`'s existing-entry
  source relation is proved, but its pool∪null value domain remains conditional
  on the table-content invariant and an exhaustive writer universe; the current
  residual is nonzero. See [[MEM_8009FD80_actor_pool]],
  `analysis/phase4_f01_static_hard_truth.json`, and
  `analysis/phase4_f01_live_gap_read_receipt.json`.

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
