---
kind: experiment
id: Experiment_-_Starry_night_sky_injection
created: 2026-07-08
updated: 2026-07-08
status: legacy_imported
confidence: confirmed
legacy_source: ObsidianVault/Experiments/Experiment - Starry night sky injection.md
aliases:
  - "Experiment - Starry night sky injection"
---

# Experiment — Starry night sky injection

> Migrated from `ObsidianVault/Experiments/Experiment - Starry night sky injection.md` during the 2026-07-08 vault completion pass. Original action: `convert_to_experiment`. Reason: Experiment note should preserve proof artifacts and link Canon claims it validates.

# Experiment — Starry night sky injection

> Turn ABL's daytime sky into a starry night by injecting GPU primitives into the frame.

| Field | Value |
|-------|-------|
| Fixture / save state | [[Fixture - starry night workbench]] → result [[Fixture - night starry]] |
| Build image / tool | none — **live debugger** (`tools/abl_starry.py`) |
| Patch | sky color cache `0x800771bc/c0/c4` (night color) + LEVEL.RAW color table `0x800c1688`; inject a MIPS routine that emits a GP0 display-list (stars) |
| APIs used | [[API - connection and auth]], `writeMemory` (MIPS inject), [[API - execution control]], [[API - gpu.readVramRect]] + [[API - visual diff]], [[API - saveState]] |

## Goal
Demonstrate end-to-end GPU primitive injection on ABL: recolor the sky to night and draw stars over it.

## Procedure (reproducible)
1. Load [[Fixture - starry night workbench]]; settle.
2. Recolor the sky to a night tone via the cache/table (see [[Experiment - G30 sky recolor]]).
3. Inject a small MIPS routine + GPU **DMA linked-list** that draws star primitives; redirect via an npc-patch; freeze with a COP0 IRQ-mask so the injected list runs deterministically (technique in [[Finding - GPU primitive injection]]).
4. `gpu.readVramRect` + `diffFrames` to verify; `saveState` to [[Fixture - night starry]].

## Result
Daytime sky → **starry night sky** rendered in-frame. Before/after/diff images: `starry_night_result/01_before_daytime.png`, `02_after_starry_night.png`, `03_diff_baseline_vs_final.png`.

## Conclusion
GPU injection works on ABL: arbitrary primitives can be drawn into the frame via injected MIPS + a GPU DMA linked-list, and the sky color is independently controllable. Tool: `tools/abl_starry.py`.

## Linked findings / functions / structures
- [[Finding - GPU primitive injection]] · [[Finding - Sky is a GP0 background fill]] · [[Finding - Sky color on-disk table]]
- [[FUNC_800639CC]] · [[MEM - Sky DRAWENV color cache 800771BC]]
## Source
`tools/abl_starry.py`; project memory (abl-gpu-injection-starry)
