---
type: experiment
status: complete
date: 2026-08-04
system: props, movers, switches, gates
phase: 4
artifacts:
  - analysis/phase4_e08_object_census.json
  - tools/phase4_e08_object_census.c
  - tools/phase4_e08_object_census.py
  - tests/test_phase4_e08_object_census.py
---

# Phase 4 E08: the per-level object census

## Question

E08's `next`: "Run the per-level object census and classify records against the
known payload/kind tables." Everything about placement tables was proven on
LEVEL01 only.

## Method

A compiled C walker (`-Werror`, self-verifying) reproduces the retail DAT
parser and **derives every table's base per file** rather than reusing
LEVEL01's constants: top-level records (`0x8001CE8C`) → the trailing advance
(`w<<7`+4) → **pass 1** (stride-0x14 placements, walk while `s16[rec+0xE] ≥ 0`)
→ **pass 2** (stride-4 registration array) → **pass 3** (cull anchors). It ran
over all **21** `LEVEL*.DAT` files.

Two implementation facts worth recording, both of which broke a first attempt:

- **The pass-2 count is SIGNED.** LEVEL01 stores `0xFFFFFFFF` there, meaning an
  *empty* pass-2 whose end sentinel *is* that word — which is exactly why
  pass-3 begins at `0x3AEC`. Read unsigned, the whole tail is unparseable.
- **The type-0x3F kind byte is at entry `+0x0C`**, not at the entry start
  (`tools/catalog_type3f.py`). Reading it at +0 produces a plausible-looking
  but meaningless histogram spread across 0x01–0xFE.

## Results

All 21 files parse; all eight cross-checks against independently committed
facts pass (`analysis/phase4_e08_object_census.json`).

**Campaign totals:** 1,058 type-0x3F contact objects · **9,097** pass-1 prop
instances · 1,684 pass-3 cull anchors · pass-2 non-empty in only 6 files.

**The contact-object kind domain is closed for placement data.** Every kind in
every level is an already-named identity — **zero unknown kinds** campaign-wide.
Totals: 774 grain, 29 telescopes/hint gems, 39 "animated construct" (0x31,
still semantically open), berries 3/11/16/2 (homing/gold/super/mega), seed
tokens 18/25/36/26/7 across 0x29–0x2D.

**FLIK letter sets are always complete.** F, L, I and K each appear exactly
**18** times campaign-wide — never a partial set. That is a structural
invariant the per-level view alone would not show.

**Every pass-1 payload pointer is unique, campaign-wide.** 9,097 records,
9,097 distinct payloads, zero nulls — generalising LEVEL01's "every payload
content-unique" observation to all 21 files. Prop *placement* is data-driven,
but prop *models* are per-instance baked blobs, so there is no shared model
library to index into.

**A documented parser path is dead in retail data.** `dat_reloc` records a
conditional relocation field gated by `flags & 0x20` (sites C/E). **No retail
record sets bit 5** — in 9,097 pass-1 records, the count is zero. The bit-3
payload-path selector, by contrast, is used heavily (4,658 pass-1, 900 pass-3).
So that branch is either legacy or authoring-only, and a mod using it would be
exercising untested code.

**Independent confirmation of E11.** The Bug Bar DAT (`LEVEL04/LEVEL1.DAT`)
reports **pass-2 entries 10, non-null 10** — reproducing
[[EXP_2026-08-02_phase4_e11_dynamic_geometry]]'s committed "exactly ten
non-null pass2 object slots with maximum index 9" from an unrelated parser and
a different starting point.

## Corrections

`src_re/prop_decor_catalog.c` says LEVEL01 has "500+" pass-1 records. The exact
figure is **484**, which is what the committed `tools/edit_pass1_records.py`
`pass1_count()` reports and what this independent C walk reproduces. The prose
was a loose approximation, not a different measurement.

## Open

- Scene→DAT binding is only partially known from committed evidence (E11 pins
  scene 14 → `LEVEL04/LEVEL1.DAT`). The census is per FILE; binding all 21
  files to scenes would need the E02-style live/needle method.
- Kind 0x31 ("animated construct") has 39 placements and no decoded semantics.
- Interaction rules, authored state and persistence/reset — the rest of E08's
  `missing` — are untouched by a placement census.

## Gates

`tests/test_phase4_e08_object_census.py` — 8 tests: the C walker compiles;
all 21 files parse with every cross-check green; no unknown kinds; balanced
FLIK sets; the all-distinct/non-null payload law; bit-5 unused while bit-3 is
heavily used; pass-2 rarity plus the E11 Bug Bar agreement; and the grain /
telescope / 0x31 totals. All pass.

## Related

[[Prop_and_foliage_catalog]] · [[EXP_2026-08-02_phase4_e11_dynamic_geometry]] ·
[[SYS_contact_objects_and_drops]]
