---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Functions/FUNC_800345CC.md
aliases: []
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Functions/FUNC_800345CC.md`
- Replacement/current location: `ObsidianVault/Canon/Functions/FUNC_800345CC_collision_resolver_-_accumulate.md`
- Archive reason: Existing function note; migrate only evidence-backed claims and link C source where available.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: FUNC_800345CC — collision resolver / accumulate
type: function
address: 0x800345CC
confidence: CONFIRMED
tags: [function, collision, physics, g29]
---
# FUNC_800345CC — collision resolve / per-axis accumulate helper

> Iterates the per-frame collision-candidate list and accumulates the resolved position that the integrator commits. Where "floor height" is computed as a swept plane clamp.

| Field | Value |
|-------|-------|
| Address | 0x800345CC (prologue addiu sp,-0x110; accumulate store `0x80035ed8`) |
| Source file | `geometry_collision_consumers.c` (G29) |
| Confidence | CONFIRMED write site; exact record→Y arithmetic UNKNOWN |

## Purpose
Walks the per-frame candidate list (`[gp+0x57c]` count, list `0x8009c230`) and accumulates the resolved position: `pos[i] += signed halfword delta[i]` for X/Y/Z, writing into [[FUNC_8003633C]]'s working buffer. The resolved Y is a **swept plane-distance clamp + stop-with-skin (−0xc0)** — the floor is a set of planes, not a scalar. Point-in-face test `0x80032610`.

## Arguments / Returns
`a0` = sp+0x18 working buffer, candidate list inputs. Writes accumulated position.

## Calls (callees)
- `fcn.80032610` — point-in-face (2D point-in-poly) test.

## Called by (callers)
- [[FUNC_8003633C]] (and alt path `fcn.80035280`).

## Globals & structures touched
- candidate list `0x8009c230` · [[MEM - Collision plane record]] · [[MEM - Collision sector table 800A7E48]].

## Evidence & confidence notes
G29 disasm `0x800347c4..0x80034b30` + read-watch established the swept-plane clamp + skin. The exact per-record Y math and the no-contact/slide-retest branches are partly open — see [[Open Questions]].

## Related
- Findings: [[Finding - Collision is planes not scalar]] · [[Finding - Collision sector table]] · [[Finding - Player Y writer FUNC_3633C]]
- Functions: [[FUNC_8003633C]] · [[FUNC_80030F60]]
- Source docs: `src_re_geometry/geometry_g29_collision_source_plan.md`
