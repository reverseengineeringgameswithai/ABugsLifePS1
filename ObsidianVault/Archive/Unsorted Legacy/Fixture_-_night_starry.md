---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Fixtures/Fixture - night starry.md
aliases:
  - "Fixture - night starry"
migration_action: needs_review
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Fixtures/Fixture - night starry.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Fixture - night starry
type: fixture
confidence: CONFIRMED
tags: [fixture, sky, gpu-injection, result]
---

# Fixture — night starry (result state)

| Field | Value |
|-------|-------|
| **Path** | `~/.local/share/duckstation/savestates/SCUS-94288_night_starry.sav` |
| **Game serial** | SCUS-94288 |

## Game state
The **finished result** of the starry-night experiment: ABL's daytime sky has been turned into a **starry night sky** by injecting GPU primitives into the frame. This is a *demonstration* state proving end-to-end GPU injection works on ABL.

## How it was produced
Via the GPU-injection toolchain — inject MIPS, an npc-patch redirect, a COP0 IRQ-mask freeze, and a GPU DMA linked-list. See [[Finding - GPU primitive injection]] and the tool `tools/abl_starry.py`. Before/after/diff screenshots are in `~/Downloads/ABL/starry_night_result/` (`01_before_daytime.png`, `02_after_starry_night.png`, `03_diff_baseline_vs_final.png`).

## Related
- Findings: [[Finding - GPU primitive injection]] · [[Finding - Sky is a GP0 background fill]]
- Experiments: [[Experiment - Starry night sky injection]]
- Workbench fixture: [[Fixture - starry night workbench]]
- Tool: `tools/abl_starry.py` · [[Tools Catalog]]
