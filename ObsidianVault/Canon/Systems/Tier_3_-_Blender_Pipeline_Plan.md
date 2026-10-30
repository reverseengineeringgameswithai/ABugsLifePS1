---
kind: system
id: Tier_3_-_Blender_Pipeline_Plan
created: 2026-07-08
updated: 2026-07-08
status: legacy_import_needs_curation
confidence: medium
source_state: original_game_or_mixed_legacy_note
legacy_source: ObsidianVault/Systems/Tier 3 - Blender Pipeline Plan.md
aliases:
  - "Tier 3 - Blender Pipeline Plan"
archived_source: ObsidianVault/Archive/Superseded/Systems_Tier_3_-_Blender_Pipeline_Plan.md
patch_policy: unknown
---

> [!warning] ⛔ OBSOLETE — Track A (CPU/OT renderer) is retired, 2026-08-11
> **Operator decision:** the CPU/OT Tier-3 renderer (`mod/caves/tier3_otrender.c`,
> `RENDER_C 0x801F0C00`, the DrawOTag hook `0x80064618`, `tier3_walls.c` collision) is
> **obsolete and must not be extended**. Its ~700-triangle / `MAXV 384 / MAXT 512` CPU
> budget cannot express a real stage, so it cannot be the custom-level engine.
>
> It also never *replaced* anything: its output is **overdraw** on top of the still-drawn
> native terrain.
>
> Retained ONLY as historical evidence and as a source of proven ideas — chiefly the
> per-face SEGMENT-plane collision derivation, which is renderer-independent and may be
> ported. Do not build new levels, tooling, or milestones on this track.
>
> Live track: the native GTE `FUNC_80010000` path (Track B) and its successor, an
> arbitrary-triangle authoring pipeline. See `docs/TIER3_RENDERER_TRACKS.md`.


# Tier_3_-_Blender_Pipeline_Plan

## Canon Status

This page was created during the 2026-07-08 migration completion pass from `ObsidianVault/Systems/Tier 3 - Blender Pipeline Plan.md`. It is a structured Canon landing page for search/linking, but the archived source remains the provenance copy. Treat specific claims as Canon only when they are supported by the evidence links, C source, or stronger curated pages.

- Legacy title: Tier-3 Blender pipeline — implementation plan (post-2026-07-03 levers)
- Archived full source: `ObsidianVault/Archive/Superseded/Systems_Tier_3_-_Blender_Pipeline_Plan.md`
- Migration action: `convert_to_canon`
- Migration confidence: `medium`
- Migration reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

## Legacy Heading Index

- `# Tier-3 Blender pipeline — implementation plan (post-2026-07-03 levers)`
- `## 0. Architecture principle (settled by this week's RE)`
- `## 1. Blender → disc export design (one manifest, five lanes)`
- `## 2. Documentation to update (as the work lands)`
- `## 3. Helper scripts / schema stubs to add`
- `## 4. Next proof-of-concept: "Playground v1" (one disc, all levers)`
- `## 5. Still to solve (ranked)`
- `## Sequencing`
- `## Related`

## Archived Source

The full legacy note is preserved at `ObsidianVault/Archive/Superseded/Systems_Tier_3_-_Blender_Pipeline_Plan.md`. It is intentionally not copied into this Canon landing page, so stale or superseded claims do not pollute Canon search results.
