---
kind: function
id: FUNC_80037320
aliases: [FUNC_80037320, 0x80037320]
address: 0x80037320
name: collision_candidate_builder
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

# FUNC_80037320 - Collision — candidate set builder

## Purpose

Builds the set of collision candidates for the player integrator to test. u3 runtime: its worker collision_probe_candidate_pass (0x80036E70) is called from here.

## Known behavior

5 callers. Calls collision_probe_candidate_pass.

## Address / identity

- Address: `0x80037320`
- Name: `collision_candidate_builder` (evidence: [[EXP_2026-07-09_understanding_u3]] + static census `analysis/functions.json`)

## Evidence

- [[EXP_2026-07-09_understanding_u3]] — runtime execTrace campaign (pristine saves).
- Census row `analysis/functions.json` (callers/callees, dynamic coverage).

## Related

See [[Address Index]] and [[SYS_function_census]].
