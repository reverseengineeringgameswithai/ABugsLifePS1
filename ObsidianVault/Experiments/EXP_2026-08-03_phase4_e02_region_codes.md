---
type: experiment
status: complete
date: 2026-08-03
system: collision region codes
phase: 4
artifacts:
  - analysis/phase4_e02_region_code_census.json
  - analysis/phase4_e02_consumer_binding.json
  - tools/phase4_e02_region_code_census.py
  - tests/test_phase4_e02.py
---

# Phase 4 E02: the complete region-code domain and every consumer branch

## Question

E02's `next`: "Enumerate all region-code values across levels; bind each code
to its consumer branch in FUNC_80038F38."

## Answer (short)

**The campaign's complete region-code domain is {0, 1, 2, 3, 4}** — proven by
an UNFILTERED census over 3,955 sectors across all 16 level anchors, using the
loader's own count global `[0x800822A0]` (no plausibility filters, unlike the
committed RCG-003 catalog which assumed 1..4). Every code is bound to its
consumer branches across all three callers of the query. Notably, **codes 2
and 3 share a byte-identical exit body**, and **code 4 suppresses checkpoint
saving**.

## Method

1. **Census, offline** (`tools/phase4_e02_region_code_census.py`): reuses the
   committed catalog's save-state RAM extractor; per save reads the sector
   count from `[0x800822A0]` (collision_source_converter canon, LEVEL01
   N=223) and dumps every sector's code halfword at
   `0x800A7E48 + i*0x30 + 0x2E`. Disc-side cross-check for LEVEL01 via the
   committed `edit_sector_region_code.py --list` (chunk-32-resident prefix):
   agreement.
2. **Binding, static from committed byte-verified hand-asm** (v5 corpus), all
   three callers of `sector_region_code_query` (0x80038F38, byte-matched C):
   the player dispatch in 0x80048138, `checkpoint_save` 0x80054C90, and the
   mover actor update 0x8004B940. EXE spot-pins in the test gate
   (dispatch head words at 0x80049644..0x8004966C; the shared fade store
   `sh v0,9328(at)` appears exactly once in the dispatch body).

## Results

Per-code binding (details in `analysis/phase4_e02_consumer_binding.json`):

| Code | Player dispatch (0x80048138) | Other consumers | Census placement |
|---|---|---|---|
| 0 | inert | — | default (3,921 sectors) |
| 1 | `FUNC_8004A700(...,a3=1)` transition A | mover update: object +0x5A=0, +0x62=2, **+0x6E=0** (retire) | bands leading INTO endings (tunnels 570-578, riverbed 292-296, city 219) |
| 2 | exit body: `[0x800823A0]=1`, fade 23, `FUNC_80050994(58,0)` | — | LEVEL01 177, riverbed_flight 334 (both live-proven, committed catalog) |
| 3 | **identical body to 2** (shared tail) | — | training 24, tunnels 579, cliffside 131, riverbed_run 297 (LEVEL02/04/05 be-here proofs in the committed catalog are code-3 sectors → live-proven) |
| 4 | gated (`+0x7E==0 && +0x92==0`) `FUNC_8004A700(...,a3=0)` transition B | **checkpoint_save bails if code==4** (no-checkpoint zones; dovetails C15) | city_entrance 220-225 |

Gates on the dispatch: query ≠ 0, exit latch `[0x800823A0]` still 0, and the
Flik gate byte (+0x82) == 1 inside the query. Nine levels expose no nonzero
codes at their anchors — exactly the conditional/boss-ending levels per the
committed objective split.

## Corrections / provenance notes

- The committed catalog's "codes 1..4" was an assumption baked into its
  filter; the unfiltered census proves it was also the truth.
- `SYS_training_ending_trigger_field.md` exists in the working tree but is
  another agent's UNCOMMITTED page — the training (24,3) row here is my
  census's own reading; the page is corroboration only.

## Open residuals (explicit)

- `FUNC_8004A700`'s destination/resource semantics (transition variants A/B)
  — per-level semantic work shared with the goal-matrix row.
- A live behavioral crossing of a code-4 checkpoint-suppression zone (static
  + committed evidence deemed sufficient for the binding; a city_entrance
  teleport test would upgrade it).
- The exit latch 0x800823A0 is multi-valued elsewhere (value 5 = a no-damage
  region state per the B06/B08 artifact) — outside this row's scope.

## Gates

`tests/test_phase4_e02.py` — 7 tests: census offline regeneration; the exact
{0..4} domain with count reconciliation; reproduction of every committed
catalog row; the conditional-ending-level negative set; the LEVEL01 disc
cross-check; binding coverage of every observed code; EXE spot-pins of the
dispatch. All pass.

## Related

[[FUNC_80038F38]] · [[MEM_800A7E48_Collision_sector_table_800A7E48]] ·
[[Level_Goal_and_Exit_Trigger_Matrix]] · [[EXP_2026-08-03_phase4_e03_ot_packet_census]]
