---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Fixtures/Fixture - g30 openfloor.md
aliases:
  - "Fixture - g30 openfloor"
migration_action: needs_review
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Fixtures/Fixture - g30 openfloor.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Fixture - g30 openfloor
type: fixture
fixture_id: x2
confidence: CONFIRMED
tags: [fixture, g30, floor, openfloor]
---

# Fixture — g30 openfloor

| Field | Value |
|-------|-------|
| **Path** | `~/.local/share/duckstation/savestates/SCUS-94288_g30_openfloor.sav` |
| **Fixture id** | `x2` (in findings store) |
| **Game serial** | SCUS-94288 |
| **Frame** | 0 (start) |

## Game state
Flik on a **big open unobstructed pebbled floor** (a different area from [[Fixture - g30 openground]]), camera Z ≈ **217790**. Chosen for a good, clean view of the **visible-ground edit** via the DAT-backed `fcn.80010000` path.

> [!warning] Walking forward from this spot **spawns an enemy + fence**. Stay put for clean render captures, or expect new geometry/objects to appear.

## Why this fixture exists / expected outcome
Best vantage to observe edits to the visible ground produced by [[FUNC_80010000]] (the DAT-backed object emitter) and its `0x80019xxx` sub-emitter — see [[Finding - Visible ground from DAT verts]]. Lowering the int16 Y at `vert+0xa` reshapes the visible floor here.

## Recommended APIs
[[API - loadState]] → settle → [[API - execTrace]] at [[FUNC_80019934]] / [[FUNC_80010000]] · [[API - accessLog]] (read-watch DAT vert source) · [[API - gpu.readVramRect]] + [[API - visual diff]].

## Related
- Findings: [[Finding - Visible ground from DAT verts]] · [[Finding - Candidate A is DAT-backed visual terrain]]
- Experiments: [[Experiment - G28 Candidate A floor Y]]
- Save catalog: [[Save States Index]]
