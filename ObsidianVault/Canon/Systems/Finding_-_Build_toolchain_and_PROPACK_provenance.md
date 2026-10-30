---
kind: system
id: Finding_-_Build_toolchain_and_PROPACK_provenance
created: 2026-07-08
updated: 2026-07-08
status: legacy_import_confirmed
confidence: confirmed
source_state: original_game_or_mixed_legacy_note
legacy_source: ObsidianVault/Findings/Finding - Build toolchain and PROPACK provenance.md
aliases:
  - "Finding - Build toolchain and PROPACK provenance"
archived_source: ObsidianVault/Archive/Superseded/Findings_Finding_-_Build_toolchain_and_PROPACK_provenance.md
patch_policy: unknown
---

# Finding_-_Build_toolchain_and_PROPACK_provenance

## Canon Status

This page was created during the 2026-07-08 migration completion pass from `ObsidianVault/Findings/Finding - Build toolchain and PROPACK provenance.md`. It is a structured Canon landing page for search/linking, but the archived source remains the provenance copy. Treat specific claims as Canon only when they are supported by the evidence links, C source, or stronger curated pages.

- Legacy title: Finding — Original build toolchain & PROPACK provenance (from on-disc dev artifacts)
- Archived full source: `ObsidianVault/Archive/Superseded/Findings_Finding_-_Build_toolchain_and_PROPACK_provenance.md`
- Migration action: `convert_to_canon`
- Migration confidence: `confirmed`
- Migration reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

## Legacy Heading Index

- `# Finding — Original build toolchain & PROPACK provenance (from on-disc dev artifacts)`
- `## The pipeline`
- `## LEVEL.RAW = PROPACK-packed lbm/bgr frames (key reframing)`
- `## Implications (what this unblocks)`
- `## Verified offline (Phase 1d/1e, 2026-06-18)`
- `## References (existing preservation research)`
- `## Related`

## Archived Source

The full legacy note is preserved at `ObsidianVault/Archive/Superseded/Findings_Finding_-_Build_toolchain_and_PROPACK_provenance.md`. It is intentionally not copied into this Canon landing page, so stale or superseded claims do not pollute Canon search results.

## Curated addition (2026-07-08): PsyQ SDK version = 4.0.0 — CONFIRMED

Full library signature matching (ghidra_psx_ldr, project ABLPsx) **auto-detected PsyQ
4.0.0** from the `Ps` library version markers embedded in `SCUS_942.88`, and 644 SDK
library functions matched under that version (libc/libgpu/libgte/libetc/libsnd/libspu/
libapi/kernel). This refines the previous "PsyQ SDK, (c) 1993-1997 Sony" evidence to a
specific SDK release, consistent with the Oct-1998 master. Toolchain picture now:
**SN PsyMake 1.11 → PsyQ SDK 4.0.0 → PROPACK 2.29 asset packing** (Traveller's Tales).

Evidence: [[EXP_2026-07-08_psyq_signature_match]] · symbol map `symbols/re_symbols.sym`
· library layout summary in [[SYS_executable_image]].
