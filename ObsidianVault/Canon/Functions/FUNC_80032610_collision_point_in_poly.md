---
kind: function
id: FUNC_80032610
aliases: [FUNC_80032610, 0x80032610]
address: 0x80032610
name: collision_point_in_poly
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

# FUNC_80032610 - Collision — point-in-polygon test

## Purpose

The core collision geometry test: determines whether a point lies within a collision polygon/sector. The biggest undocumented resident leaf (8124 B, 0 jal — pure fixed-point math).

## Known behavior

3 callers (collision resolve path). Leaf: no calls out. Dynamic-covered across levels.

## Address / identity

- Address: `0x80032610`
- Name: `collision_point_in_poly` (evidence: [[EXP_2026-07-09_understanding_u3]] + static census `analysis/functions.json`)

## Evidence

- [[EXP_2026-07-09_understanding_u3]] — runtime execTrace campaign (pristine saves).
- Census row `analysis/functions.json` (callers/callees, dynamic coverage).

## Related

See [[Address Index]] and [[SYS_function_census]].
