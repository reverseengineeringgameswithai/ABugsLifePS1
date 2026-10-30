---
kind: system
id: Tier_3_-_Level_Replacement_Phases
created: 2026-07-08
updated: 2026-07-08
status: legacy_import_needs_curation
confidence: medium
source_state: original_game_or_mixed_legacy_note
legacy_source: ObsidianVault/Systems/Tier 3 - Level Replacement Phases.md
aliases:
  - "Tier 3 - Level Replacement Phases"
archived_source: ObsidianVault/Archive/Superseded/Systems_Tier_3_-_Level_Replacement_Phases.md
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


# Tier_3_-_Level_Replacement_Phases

## Canon Status

This page was created during the 2026-07-08 migration completion pass from `ObsidianVault/Systems/Tier 3 - Level Replacement Phases.md`. It is a structured Canon landing page for search/linking, but the archived source remains the provenance copy. Treat specific claims as Canon only when they are supported by the evidence links, C source, or stronger curated pages.

- Legacy title: Tier 3 — Level Replacement Phases
- Archived full source: `ObsidianVault/Archive/Superseded/Systems_Tier_3_-_Level_Replacement_Phases.md`
- Migration action: `convert_to_canon`
- Migration confidence: `medium`
- Migration reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

## Legacy Heading Index

- `# Tier 3 — Level Replacement Phases`
- `## 1. Project goal & non-goals`
- `### Goal`
- `### Non-goals (explicit — do NOT do these)`
- `## 2. Current architecture & its proven limitations`
- `### Proven limitation (the crux — why OG content flickers)`
- `## 3. Target architecture`
- `## 4. Dependency map — must remain vs. removable at source`
- `### MUST REMAIN (engine depends on it — the intended host substrate)`
- `### REMOVABLE AT SOURCE NOW (separable; mostly existing tooling)`
- `### HARD PIECE (only if residual after the above)`
- `## 5. Phased implementation plan (success criteria + rollback)`
- `### Phase 0 — LEVEL00 leak fix (engine was leaking OUT of LEVEL01)  ✅ DONE (2026-07-01)`
- `### Phase 1 — EVIDENCE PASS: classify what actually leaks  ✅ DONE (2026-07-01)`
- `### Phase 2 — Object source-removal (biggest, low-risk win)  ✅ DONE (2026-07-01)`
- `### Phase 3 — Chunk-35 terrain source-removal  ❌ REVERTED (2026-07-01) — FUNC_800172DC also draws FLIK`
- `### Phase 4 — Residual terrain builders  ✅ RESOLVED-BY-REFRAME (2026-07-01) — GRASS removed; DIRT is now the KEPT backdrop, not a target`
- `### Phase 5 — Retire the heuristic + finalize  ✅ DONE (2026-07-01)`
- `## 6. Evidence log`
- `## 7. Open questions, risks & remaining RE tasks`
- `## 8. Definition of Done — true custom LEVEL01`

## Archived Source

The full legacy note is preserved at `ObsidianVault/Archive/Superseded/Systems_Tier_3_-_Level_Replacement_Phases.md`. It is intentionally not copied into this Canon landing page, so stale or superseded claims do not pollute Canon search results.
