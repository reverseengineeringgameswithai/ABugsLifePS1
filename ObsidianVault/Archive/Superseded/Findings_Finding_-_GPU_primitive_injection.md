---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - GPU primitive injection.md
aliases:
  - "Finding - GPU primitive injection"
migration_action: split
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - GPU primitive injection.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_GPU_primitive_injection.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Finding - GPU primitive injection
type: finding
confidence: CONFIRMED
gstep: n/a (starry-night)
tags: [finding, rendering, gpu, injection, sky]
---

# Finding — GPU primitive injection (daytime → starry night)

> End-to-end proof that arbitrary GPU primitives can be drawn into an ABL frame via the DuckStation debugger: the daytime sky was turned into a **starry night** by injecting a GPU DMA linked-list.

**Confidence:** CONFIRMED · **Tool:** `tools/abl_starry.py`

## Summary
The technique (per project memory `abl-gpu-injection-starry`):
1. **Inject MIPS** code into guest RAM and redirect execution to it via an **npc-patch** (next-PC) redirect.
2. **Freeze interrupts** with a COP0 IRQ-mask (so the injected routine runs uninterrupted).
3. Have the injected routine submit a **GPU DMA linked-list** (GP0 display list) that draws the star primitives over the sky.
Because the sky is a flat fill ([[Finding - Sky is a GP0 background fill]]), stars must be *drawn over* it rather than swapped into a texture.

## Evidence
- Before/after/diff screenshots in `~/Downloads/ABL/starry_night_result/` (`01_before_daytime.png`, `02_after_starry_night.png`, `03_diff_baseline_vs_final.png`).
- Result captured as the fixture [[Fixture - night starry]]; workbench [[Fixture - starry night workbench]].

## Related functions
[[FUNC_800639CC]] (the engine's own sky fill, drawn under the injected stars)

## Related memory structures
[[MEM - Sky DRAWENV color cache 800771BC]]

## Related experiments
[[Experiment - Starry night sky injection]]

## Related fixtures / save states
[[Fixture - night starry]] · [[Fixture - starry night workbench]]

## DuckStation APIs used
[[API - execution control]] · [[API - scatterWrite]] · [[API - gpu.readVramRect]] · [[API - visual diff]] · [[API - saveState]]

## Next steps / follow-up
**Superseded for the night-sky goal by [[Finding - Persistent night render hook]]** — a per-frame trampoline that draws a big moon + stars into the back buffer every frame (flicker-free, persists during gameplay) and removes the horizon haze at its source ([[FUNC_8003E928]]). This note documents the original one-shot/frozen-frame overlay; the persistent version is the production result.

Generalize the injection harness as a reusable "draw arbitrary primitives" tool; combine with terrain/collision levers for richer scene edits.

## Source
Project memory `abl-gpu-injection-starry`; tool `tools/abl_starry.py`; `tools/vramdiff.py`
