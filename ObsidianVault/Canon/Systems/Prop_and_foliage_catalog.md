---
kind: system
id: Prop_and_foliage_catalog
created: 2026-07-08
updated: 2026-07-08
status: legacy_import_needs_curation
confidence: medium
source_state: original_game_or_mixed_legacy_note
legacy_source: ObsidianVault/Systems/Prop and foliage catalog.md
aliases:
  - "Prop and foliage catalog"
archived_source: ObsidianVault/Archive/Superseded/Systems_Prop_and_foliage_catalog.md
patch_policy: unknown
---

# Prop_and_foliage_catalog

## Canon Status

This page was created during the 2026-07-08 migration completion pass from `ObsidianVault/Systems/Prop and foliage catalog.md`. It is a structured Canon landing page for search/linking, but the archived source remains the provenance copy. Treat specific claims as Canon only when they are supported by the evidence links, C source, or stronger curated pages.

- Legacy title: Prop & foliage catalog — 13 fixtures surveyed + the payload-swap lever
- Archived full source: `ObsidianVault/Archive/Superseded/Systems_Prop_and_foliage_catalog.md`
- Migration action: `convert_to_canon`
- Migration confidence: `medium`
- Migration reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

## Legacy Heading Index

- `# Prop & foliage catalog — 13 fixtures surveyed + the payload-swap lever`
- `## The headline lever (NEW, live-proven)`
- `## Catalog`
- `## Hitboxes — the architectural verdict`
- `## Tier-3 / Blender leverage`
- `## Residuals — 2026-07-03 closeout pass`
- `## Related`

## Archived Source

The full legacy note is preserved at `ObsidianVault/Archive/Superseded/Systems_Prop_and_foliage_catalog.md`. It is intentionally not copied into this Canon landing page, so stale or superseded claims do not pollute Canon search results.

## Campaign-wide object census (E08, 2026-08-04)

A compiled C walker reproduced the retail DAT parser with **per-file base
derivation** (no LEVEL01 constants assumed) across all **21** `LEVEL*.DAT`
files: `analysis/phase4_e08_object_census.json`, gated by
`tests/test_phase4_e08_object_census.py`.

**Totals:** 1,058 type-0x3F contact objects · **9,097 pass-1 prop instances** ·
1,684 pass-3 cull anchors · pass-2 non-empty in only 6 files.

New campaign-level laws:

- **Every pass-1 payload pointer is unique and non-null** — 9,097 records,
  9,097 distinct payloads. LEVEL01's "every payload content-unique" holds
  campaign-wide, so prop *models* are per-instance baked blobs with no shared
  library, even though *placement* is fully data-driven.
- **The `flags & 0x20` relocation path is DEAD in retail data.** Bit 5 is set
  on zero of 9,097 pass-1 records, while the bit-3 payload-path selector is
  used heavily (4,658 pass-1, 900 pass-3). A mod using bit 5 would exercise
  untested parser code.
- **The contact-object kind domain is closed for placement data**: zero unknown
  kinds campaign-wide. 774 grain, 29 telescopes, 39 kind-0x31 "animated
  construct" (semantics still open), berries 3/11/16/2, seed tokens across
  0x29–0x2D.
- **FLIK letter sets are always complete** — F/L/I/K each appear exactly 18
  times campaign-wide, never a partial set.

Independent confirmation: the Bug Bar DAT reports pass-2 entries 10 / non-null
10, reproducing [[EXP_2026-08-02_phase4_e11_dynamic_geometry]]'s committed
"exactly ten non-null pass2 slots" from a different parser.

**Correction:** `src_re/prop_decor_catalog.c`'s "500+ records in LEVEL01" is a
loose approximation; the exact count is **484**, matching the committed
`edit_pass1_records.py` and this independent walk.

Two parser facts worth carrying: the **pass-2 count is signed** (LEVEL01's
`0xFFFFFFFF` means an empty pass-2 whose sentinel is that word, which is why
pass-3 starts at 0x3AEC), and the **type-0x3F kind byte sits at entry +0x0C**.

See [[EXP_2026-08-04_phase4_e08_object_census]].

## Runtime classification and row boundary (E08 follow-up, 2026-08-04)

The runtime follow-up closes the catalog's high-value semantic frontier and
marks E08 **substantiated partial, bounded-exhausted**.

Kind `0x31` is an ordinal proximity-emitter family, not an unidentified
passive prop and not telescope/checkpoint activation. Across eight DATs its 39
records form seven groups of five plus one group of four. Every record begins
with `Y=-600`, visibility status zero and rest height zero. The projector
rewrites the status every frame, so it is visibility/eligibility rather than
authored persistent state.

When close, below the rest-height threshold and on alternating phase zero,
the resident path constructs metadata-B rows `84..88` as `83 + ordinal` with
metadata-A row 21. The five rows share action/type/lifetime fields and differ
in their final RGB-shaped byte triplets. Exact color/pixel identity remains a
presentation inference; the constructor/gate law is pristine-ASM verified.

Correction: `0x80057620` is the common five-object burst/finalize helper for
ordinary pickup kinds. The branch at `0x80053CA8` makes kinds `0x30` and
`0x31` bypass it. Kind `0x31` has its own exact-height action at `0x800545A0`.

Pass-1 props remain passive render records with collision authored separately.
Scripted movers/switches, grain gates and dynamic geometry are owned by E07,
E09 and E11 respectively rather than duplicated here. See
[[EXP_2026-08-04_phase4_e08_runtime_semantics]].
