---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Functions/FUNC_800639CC.md
aliases: []
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Functions/FUNC_800639CC.md`
- Replacement/current location: `ObsidianVault/Canon/Functions/FUNC_800639CC_DRAWENV_background-fill_builder.md`
- Archive reason: Existing function note; migrate only evidence-backed claims and link C source where available.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: FUNC_800639CC — DRAWENV background-fill builder
type: function
address: 0x800639CC
confidence: CONFIRMED
tags: [function, rendering, sky, drawenv, g30]
---
# FUNC_800639CC — GP0 0x02 background-fill (sky) builder

> Builds the GP0 0x02 background-fill command from the active DRAWENV RGB bytes each frame. The function behind the "sky is a fill, not an image" finding.

| Field | Value |
|-------|-------|
| Address | 0x800639CC |
| Source file | disasm (G30) |
| Confidence | CONFIRMED |

## Purpose
Builds the GP0 `0x02BBGGRR` background-fill command from the active DRAWENV RGB bytes. The submitted transient command copies (`0x801cc3c8 / 0x801e1384`) are rebuilt each frame — so to recolor the sky you patch the upstream cache/table, not the transient command.

## Arguments / Returns
Reads DRAWENV RGB; emits the fill command. execTrace observed `s0=0x801cc390, a1=0x801cc3c8, v0=0x02db5931` from DRAWENV bytes `31 59 db`.

## Calls (callees)
- GPU submit primitives.

## Called by (callers)
- per-frame render path.

## Globals & structures touched
- [[MEM - Sky DRAWENV color cache 800771BC]] (RGB source `0x800771bc/c0/c4`).

## Evidence & confidence notes
G30 §19 confirmed via execTrace + gpu.readVramRect/diff: red cache patch → VRAM `0x001f`, green → `0x03e0`. No VRAM bitmap exists for the sky. Findings store id f3.

## Related
- Findings: [[Finding - Sky is a GP0 background fill]] · [[Finding - Sky color on-disk table]] · [[Finding - GPU primitive injection]]
- Memory: [[MEM - Sky DRAWENV color cache 800771BC]]
- Experiments: [[Experiment - G30 sky recolor]] · [[Experiment - Starry night sky injection]]
- Source docs: `src_re_geometry/geometry_g30_terrain_render_source_plan.md` §19
