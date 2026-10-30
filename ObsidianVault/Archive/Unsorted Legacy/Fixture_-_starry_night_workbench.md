---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Fixtures/Fixture - starry night workbench.md
aliases:
  - "Fixture - starry night workbench"
migration_action: needs_review
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Fixtures/Fixture - starry night workbench.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Fixture - starry night workbench
type: fixture
confidence: CONFIRMED
tags: [fixture, sky, gpu-injection, workbench]
---

# Fixture — starry night workbench

| Field | Value |
|-------|-------|
| **Path** | `~/.local/share/duckstation/savestates/SCUS-94288_starry_night_workbench.sav` |
| **Game serial** | SCUS-94288 |

## Game state
The **working bench** for developing the starry-night GPU injection — a daytime scene paused at a point where the injection toolchain (`tools/abl_starry.py`) can be iterated. Load this to re-run or extend the injection; save the outcome to [[Fixture - night starry]].

## Recommended APIs
[[API - loadState]] · injection via the MIPS-patch / GPU-DMA-linked-list flow (see [[Finding - GPU primitive injection]]) · [[API - gpu.readVramRect]] + [[API - visual diff]] to verify, [[API - saveState]] to capture the result.

## Related
- Findings: [[Finding - GPU primitive injection]]
- Experiments: [[Experiment - Starry night sky injection]]
- Result fixture: [[Fixture - night starry]] · Tool: `tools/abl_starry.py`
