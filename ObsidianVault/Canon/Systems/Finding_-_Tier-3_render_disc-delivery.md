---
kind: system
id: Finding_-_Tier-3_render_disc-delivery
created: 2026-07-08
updated: 2026-07-08
status: legacy_import_needs_curation
confidence: medium
source_state: original_game_or_mixed_legacy_note
legacy_source: ObsidianVault/Findings/Finding - Tier-3 render disc-delivery.md
aliases:
  - "Finding - Tier-3 render disc-delivery"
archived_source: ObsidianVault/Archive/Superseded/Findings_Finding_-_Tier-3_render_disc-delivery.md
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


# Finding_-_Tier-3_render_disc-delivery

## Canon Status

This page was created during the 2026-07-08 migration completion pass from `ObsidianVault/Findings/Finding - Tier-3 render disc-delivery.md`. It is a structured Canon landing page for search/linking, but the archived source remains the provenance copy. Treat specific claims as Canon only when they are supported by the evidence links, C source, or stronger curated pages.

- Legacy title: Finding — Tier-3 render needs its own disc file (LEVEL.DAT/RAW are LBA-full)
- Archived full source: `ObsidianVault/Archive/Superseded/Findings_Finding_-_Tier-3_render_disc-delivery.md`
- Migration action: `convert_to_canon`
- Migration confidence: `medium`
- Migration reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

## Legacy Heading Index

- `# Finding — Tier-3 render needs its own disc file (LEVEL.DAT/RAW are LBA-full)`
- `## The constraint: no spare on-disc room next to the level files`
- `## The reusable loader: `FUNC_80046330(name, dest)``
- `### Filename format (3b.R step 1 — CONFIRMED LIVE 2026-06-26)`
- `## IMPLEMENTED + VERIFIED (2026-06-26)`
- `## COLD-BOOT FIX — RESOLVED (2026-06-26, commit a7176ec)`
- `## Original plan (for reference)`
- `## SESSION LOG — 2026-06-26 live-fire debugging (5 bugs found; 4 fixed, 1 open)`
- `### OPEN — render code overwritten in complex/turned-around views (RI crash)`
- `## Related`

## Archived Source

The full legacy note is preserved at `ObsidianVault/Archive/Superseded/Findings_Finding_-_Tier-3_render_disc-delivery.md`. It is intentionally not copied into this Canon landing page, so stale or superseded claims do not pollute Canon search results.
