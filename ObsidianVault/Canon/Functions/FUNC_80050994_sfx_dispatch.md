---
kind: function
id: FUNC_80050994
aliases: [FUNC_80050994, 0x80050994]
address: 0x80050994
name: sfx_dispatch
status: static_seen
confidence: confirmed
source_state: original_game
system: []
calls: []
reads: []
writes: []
uses_tables: []
related_constants: []
related_hooks: []
evidence: [EXP_2026-07-09_understanding_u3]
src_paths: [symbols/re_symbols.sym, analysis/functions.json]
patch_policy: unknown
---

# FUNC_80050994 - Audio — SFX dispatch

## Purpose

The most-called audio entry (12 callers): dispatches a sound-effect request to the voice manager / SPU. The trigger point most gameplay SFX route through.

## Known behavior

12 callers. The SFX request funnel.

## Address / identity

- Address: `0x80050994`
- Name: `sfx_dispatch` (evidence: [[EXP_2026-07-09_understanding_u3]] + static census `analysis/functions.json`)

## Evidence

- [[EXP_2026-07-09_understanding_u3]] — runtime execTrace campaign (pristine saves).
- Census row `analysis/functions.json` (callers/callees, dynamic coverage).

## Related

See [[Address Index]] and [[SYS_function_census]].
