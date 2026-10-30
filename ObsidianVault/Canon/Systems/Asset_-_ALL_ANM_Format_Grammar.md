---
kind: system
id: Asset_-_ALL_ANM_Format_Grammar
created: 2026-07-08
updated: 2026-07-08
status: legacy_import_needs_curation
confidence: medium
source_state: original_game_or_mixed_legacy_note
legacy_source: ObsidianVault/Assets/Asset - ALL ANM Format Grammar.md
aliases:
  - "Asset - ALL ANM Format Grammar"
archived_source: ObsidianVault/Archive/Superseded/Assets_Asset_-_ALL_ANM_Format_Grammar.md
patch_policy: unknown
---

# Asset_-_ALL_ANM_Format_Grammar

## Canon Status

This page was created during the 2026-07-08 migration completion pass from `ObsidianVault/Assets/Asset - ALL ANM Format Grammar.md`. It is a structured Canon landing page for search/linking, but the archived source remains the provenance copy. Treat specific claims as Canon only when they are supported by the evidence links, C source, or stronger curated pages.

- Legacy title: Asset — `.ALL` / `.ANM` format grammar (editor-safe baseline)
- Archived full source: `ObsidianVault/Archive/Superseded/Assets_Asset_-_ALL_ANM_Format_Grammar.md`
- Migration action: `convert_to_canon`
- Migration confidence: `medium`
- Migration reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

## Legacy Heading Index

- `# Asset — `.ALL` / `.ANM` format grammar (editor-safe baseline)`
- `## File families inspected`
- `## `.ALL` — model (grammar — round-trip VALIDATED 78/78, 2026-06-22)`
- `## `.ANM` — animation (grammar — round-trip VALIDATED 58/58, fully field-typed, 2026-06-22)`
- `## Relationship to LEVEL.RAW meshes`
- `## Parser / closure status — round-trip VALIDATED (2026-06-22; GAP-0026)`
- `## Minor open details (non-blocking)`
- `## Modding relevance & safe-editing constraints`
- `## Related`

## Archived Source

The full legacy note is preserved at `ObsidianVault/Archive/Superseded/Assets_Asset_-_ALL_ANM_Format_Grammar.md`. It is intentionally not copied into this Canon landing page, so stale or superseded claims do not pollute Canon search results.

## Runtime Lane Semantics

Static reconstruction of `0x8005F110` now establishes the transform tuple
used by the dual-animation crossfade path. Dense frame lanes `0/2/4` are
translation, lanes `6/8/10` are 12-bit wrapped Euler angles, and lanes
`12/14/16` form an optional three-value tuple gated by the `n10` metadata
bitset. Results are written into 84-byte bone-transform records at
`0x80089F58`. See [[FUNC_8005F110_ANM_crossfade_sampler]].
