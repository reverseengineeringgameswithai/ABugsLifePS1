---
kind: function
id: FUNC_80038090
aliases: [FUNC_80038090, 0x80038090]
address: 0x80038090
name: point_in_polygon_region_test
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

# FUNC_80038090 - Collision — region point-in-polygon test

## Purpose

A second point-in-polygon variant used for region/sector classification (3512 B leaf, 0 jal). Distinct from collision_point_in_poly; feeds region-code lookups (exit/trigger sectors).

## Known behavior

4 callers. Leaf. Not a mergedRegion (verified in decomp v5).

## Address / identity

- Address: `0x80038090`
- Name: `point_in_polygon_region_test` (evidence: [[EXP_2026-07-09_understanding_u3]] + static census `analysis/functions.json`)

## Evidence

- [[EXP_2026-07-09_understanding_u3]] — runtime execTrace campaign (pristine saves).
- Census row `analysis/functions.json` (callers/callees, dynamic coverage).

## Related

See [[Address Index]] and [[SYS_function_census]].
