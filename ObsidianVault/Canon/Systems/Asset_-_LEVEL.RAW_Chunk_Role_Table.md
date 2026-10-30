---
kind: system
id: Asset_-_LEVEL.RAW_Chunk_Role_Table
created: 2026-07-08
updated: 2026-07-08
status: legacy_import_confirmed
confidence: confirmed
source_state: original_game_or_mixed_legacy_note
legacy_source: ObsidianVault/Assets/Asset - LEVEL.RAW Chunk Role Table.md
aliases:
  - "Asset - LEVEL.RAW Chunk Role Table"
archived_source: ObsidianVault/Archive/Superseded/Assets_Asset_-_LEVEL.RAW_Chunk_Role_Table.md
patch_policy: unknown
---

# Asset_-_LEVEL.RAW_Chunk_Role_Table

## Canon Status

This page was created during the 2026-07-08 migration completion pass from `ObsidianVault/Assets/Asset - LEVEL.RAW Chunk Role Table.md`. It is a structured Canon landing page for search/linking, but the archived source remains the provenance copy. Treat specific claims as Canon only when they are supported by the evidence links, C source, or stronger curated pages.

- Legacy title: Asset — LEVEL.RAW per-chunk role table (LEVEL01)
- Archived full source: `ObsidianVault/Archive/Superseded/Assets_Asset_-_LEVEL.RAW_Chunk_Role_Table.md`
- Migration action: `split`
- Migration confidence: `confirmed`
- Migration reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

## Legacy Heading Index

- `# Asset — LEVEL.RAW per-chunk role table (LEVEL01)`
- `## Method / evidence basis`
- `## Region summary`
- `## Full table (key columns)`
- `## Modding relevance (priority chunks)`
- `## Next actions`
- `## Related`

## Archived Source

The full legacy note is preserved at `ObsidianVault/Archive/Superseded/Assets_Asset_-_LEVEL.RAW_Chunk_Role_Table.md`. It is intentionally not copied into this Canon landing page, so stale or superseded claims do not pollute Canon search results.

## Update 2026-08-04 — markers 0x28..0x5F are frontend image resources

Chunks whose subtype marker is in `0x28..0x5F` are **not** decoded by the loader.
It records each one's decompressed address in a marker-indexed pointer table and
moves on; the frontend uploads them to VRAM later. All 46 such chunks in the
retail game live in `LEVEL00` and are its art — menu icons, pre-rendered UI text
(the memory-card atlas among them), and the title screen.

Their two header layouts, the three tables, the consumers, and the size law that
all 46 satisfy exactly are in [[SYS_registered_chunk_image_resources]].
