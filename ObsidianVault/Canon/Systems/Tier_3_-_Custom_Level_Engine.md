---
kind: system
id: Tier_3_-_Custom_Level_Engine
created: 2026-07-08
updated: 2026-07-08
status: legacy_import_needs_curation
confidence: medium
source_state: original_game_or_mixed_legacy_note
legacy_source: ObsidianVault/Systems/Tier 3 - Custom Level Engine.md
aliases:
  - "Tier 3 - Custom Level Engine"
archived_source: ObsidianVault/Archive/Superseded/Systems_Tier_3_-_Custom_Level_Engine.md
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


# Tier_3_-_Custom_Level_Engine

## Canon Status

This page was created during the 2026-07-08 migration completion pass from `ObsidianVault/Systems/Tier 3 - Custom Level Engine.md`. It is a structured Canon landing page for search/linking, but the archived source remains the provenance copy. Treat specific claims as Canon only when they are supported by the evidence links, C source, or stronger curated pages.

- Legacy title: Tier 3 — Custom Level Engine (hosted inside ABL)
- Archived full source: `ObsidianVault/Archive/Superseded/Systems_Tier_3_-_Custom_Level_Engine.md`
- Migration action: `convert_to_canon`
- Migration confidence: `medium`
- Migration reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

## Legacy Heading Index

- `# Tier 3 — Custom Level Engine (hosted inside ABL)`
- `## Vision`
- `## Why a custom engine (not native-format authoring)`
- `## Architecture`
- `## ROADMAP — remaining tracks (authoritative path forward, 2026-06-27)`
- `### Track A — Gameplay content (objects + goal): make a Tier-3 level PLAYABLE  ★ recommended next`
- `### Track B — Visual cleanup ("step 4"): pure custom view`
- `### Track C — Per-surface textures + Blender UVs`
- `### Track D — Scale up (caps + triangle budget)`
- `### Track E — Feel polish (small, anytime)`
- `### Recommended sequencing`
- `## OPEN GAPS — object population & true level-replace (operator review, 2026-06-28)`
- `### GAP-T3-1 — Differentiated objects come from NATIVE objects, not cave markers`
- `### GAP-T3-2 — Tokens / per-kind counters (powers up seed levels)`
- `### GAP-T3-3 — FLIK letters: are they a collectible SET? (RE task — operator wants this solved)`
- `### GAP-T3-4 — Enemies: relocate SPAWN only, no AI (operator-scoped) — ✅ RESOLVED for stationary enemies (2026-06-28)`
- `### GAP-T3-5 — TRUE level-replace (operator question: does our code REPLACE terrain in memory, or hide it?)`
- `### GAP-T3-6 — The native-object ↔ custom-floor seam — ✅ RESOLVED with FLIK pin caveat (2026-06-29)`
- `### GAP-T3-7 — Level SIZE ceiling: a fixed global tri/vert budget does not scale to a real level (operator finding, 2026-07-04)`
- `### Phase 4 — integration: author geometry + native objects in ONE build — ✅ TOOLING DONE (2026-06-28)`
- `#### Phase 4b — EXACT OBJECT COUNT-CONTROL ✅ DONE + live-verified (2026-06-28)`
- `#### Phase 4c — original-texture fidelity investigation + Track-D budget raise (2026-06-28)`
- `#### Phase 4d — REAL framerate lag found + distance-cull fix (2026-06-28)`
- `#### Phase 4e — CORRECTION: the lag is CPU-bound (software clip), NOT GPU fill (2026-06-28)`

## Archived Source

The full legacy note is preserved at `ObsidianVault/Archive/Superseded/Systems_Tier_3_-_Custom_Level_Engine.md`. It is intentionally not copied into this Canon landing page, so stale or superseded claims do not pollute Canon search results.
