---
kind: system
id: Finding_-_Longer_FMV_playback_(normal-speed_extension_RE)
created: 2026-07-08
updated: 2026-07-08
status: legacy_import_needs_curation
confidence: medium
source_state: original_game_or_mixed_legacy_note
legacy_source: ObsidianVault/Findings/Finding - Longer FMV playback (normal-speed extension RE).md
aliases:
  - "Finding - Longer FMV playback (normal-speed extension RE)"
archived_source: ObsidianVault/Archive/Superseded/Findings_Finding_-_Longer_FMV_playback_(normal-speed_extension_RE).md
patch_policy: unknown
---

# Finding_-_Longer_FMV_playback_(normal-speed_extension_RE)

## Canon Status

This page was created during the 2026-07-08 migration completion pass from `ObsidianVault/Findings/Finding - Longer FMV playback (normal-speed extension RE).md`. It is a structured Canon landing page for search/linking, but the archived source remains the provenance copy. Treat specific claims as Canon only when they are supported by the evidence links, C source, or stronger curated pages.

- Legacy title: Finding — Longer FMV playback (normal-speed extension RE)
- Archived full source: `ObsidianVault/Archive/Superseded/Findings_Finding_-_Longer_FMV_playback_(normal-speed_extension_RE).md`
- Migration action: `convert_to_canon`
- Migration confidence: `medium`
- Migration reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

## Legacy Heading Index

- `# Finding — Longer FMV playback (normal-speed extension RE)`
- `## The cap = a hardcoded per-movie frame-count table in FMV.BIN (SOLVED)`
- `## What was proven`
- `### 1. Authoring an arbitrary-length STR (offline, proven)`
- `### 2. Disc rebuild with an LBA reflow (tool: `tools/build_long_fmv_disc.py`)`
- `### 3. Longer STR LOADS + STREAMS by name (CONFIRMED live) — resolves [[Blocker - RE depth is LEVEL01-only]] GAP-0025 for FMV`
- `## The blocker: playback length is capped by game logic, not the file`
- `## Session 2 (2026-07-04) — termination chain pinned; trigger still in the overlay`
- `## Repro / fixtures`

## Archived Source

The full legacy note is preserved at `ObsidianVault/Archive/Superseded/Findings_Finding_-_Longer_FMV_playback_(normal-speed_extension_RE).md`. It is intentionally not copied into this Canon landing page, so stale or superseded claims do not pollute Canon search results.
