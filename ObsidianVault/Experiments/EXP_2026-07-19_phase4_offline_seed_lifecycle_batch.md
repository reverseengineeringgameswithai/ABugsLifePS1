---
type: experiment
status: complete
date: 2026-07-19
system: Phase 4 offline trace analysis
phase: 4
---

# Phase 4 offline seed-lifecycle batch

This iteration consumed the coherent current rank-1–3 cluster:
`A09_seed_pickup_drop`, `A14_plant_seed`, and `A15_uproot_plant`. All three
rows remain open. The work used only pristine-control-matched retained
frame-boundary capsules and the exact archived reader. No DuckStation process
was launched and no new fixture was requested.

## Inputs and selection

- The acceptance contract and persistent context passed their SHA-256
  sidecars: `ee05939d6643dcbee9a62569b78a1523351d5decb6540ee9ac5571d5bebbfc63`
  and `5be3a6d98d3ff83520e012a72cda0a02ce70edec9c2cd090ec40d88df3bac578`.
- Recursive inventory found 110 Phase-4 files and 147 broader movie-tree
  files. The selected movie/save pairs are centrally hash-pinned and the
  capsule index independently matches pristine mounted/save media. Backups,
  filename semantics, and JSON serial strings were not treated as media proof.
- Capsule preservation passed 50/50 for 2,442,984,379 external bytes. The
  reader is
  `~/Downloads/ABL-external-evidence/duckstation-tools/trace_capsule_query-v1-20260718.py`,
  SHA-256 `b3898f928800efad5a949d1369aa65d786067505e0ed915eec8fdb99f0aa1dde`.
- The pre-selection queue was 16 complete/91 open, with nine
  `offline_ready`, 24 `offline_partial`, six `live_required`, and 68
  `no_capsule`. A09/A14/A15 were the three highest-ranked open
  `offline_ready` rows and joined two unique capsules.

## Offline commands and preservation

```bash
python3 tools/phase4_trace_capsules.py \
  --movie-root ~/Downloads/ABL/movies/Phase4 \
  --capsule-root ~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v2 \
  --comparison-root ~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v1 \
  --require-byte-identical-comparison \
  --binary-snapshot ~/Downloads/ABL-external-evidence/duckstation-binaries/duckstation-qt-trace-capsule-v1-20260718 \
  --offline-reader-snapshot ~/Downloads/ABL-external-evidence/duckstation-tools/trace_capsule_query-v1-20260718.py \
  --check

python3 tools/phase4_offline_queue.py \
  --movie-root ~/Downloads/ABL/movies --write

python3 tools/phase4_offline_seed_lifecycle_batch.py \
  --external-output ~/Downloads/ABL-external-evidence/derived/Phase4/seed-lifecycle-v1/index.json \
  --write
```

The tracked summary retains all 36 exact queue commands—18 for A09 and nine
each for A14/A15—in
`analysis/phase4_offline_seed_lifecycle_batch.json`. They cover full capsule
summaries and hotspots plus player, actor, contact, plant/cursor, VRAM, and
SPU-RAM windows. The generator verifies the exact reader, capsule manifests,
movie bytes, declared start states, record counts, and per-domain hashes.

All 6,025 records from the two original campaign capsules and the later
hash-pinned A10 carry supplemental were scanned once into the external
register/RAM/VRAM/SPU-RAM/block-flow index. It is 25,730,624 bytes, SHA-256
`64edaa57ce386f2065fc26eae6ef5d7ed66a13cdf7077f281232f56ab50310c5`.
Git retains only its generator/source contract, preservation hash, bounded
summary, and falsifiable tests—not movie, save, capsule, or reconstructed
frame bytes.

## Observations

### A09 carry, release, and post-release motion

The corrected actor pool begins at `0x8009FD80`. The moving A09 seed is id 11
in slot 20 (`0x800A07D0`), not a record at the old slot-1 probe. Exact
attachment—seed X/Z equal player X/Z and player Y minus seed Y equals
19,200—holds over frames 146–173, 280–557, and 680–697. Pickup Square presses
at 111/245/644 precede attachment by 35/35/36 frames. Later presses at
171/556/696 precede detachment at 174/558/698 by 3/2/2 frames.

At those releases the stored X/Z velocity pairs are `(-71,-1022)`,
`(-71,-1022)`, and `(-18,+1023)`. A horizontal component reverses at frames
192/562/720, and the seed first holds a stable position for at least ten
records at 206/606/746. This confirms three successful releases followed by
direction changes and stable outcomes. It does not identify a wall, collision
primitive, geometry, release writer, or rebound cause.

### A14 planting

The moving blue seed is actor slot 1, fixture-specific address `0x8009FE04`.
Its four +20,480 Y episodes run 102–120, 1012–1030, 2056–2074, and 2932–2950.
Each ends at a plant creation: frames 120/1030/2074/2950, types 7/7/6/7, with
cursor transitions 0→1→2→3→4. Nearest Cross presses precede creation by
50/63/42/52 frames. These are exact frame joins, not gate/writer attribution.

### A15 uproot and the +0x2E correction

The four -20,483 Y episodes run 702–728, 1648–1674, 2736–2762, and 3706–3732.
Nearest Square presses precede their starts by 45/53/52/53 frames. Plant types
clear at 754/1704/2794/3762, or 26/30/32/30 frames after descent ends.

At retirement, raw slot byte `+0x2E` retains values 5/5/13/5 for plant types
7/7/6/7. This falsifies the older universal “5 means player uproot” claim.
The byte is retained conservatively as subtype-owned raw lifecycle state;
exact teardown writers and the full subtype domain remain unknown.

## Decision and remaining unknowns

The regenerated queue derives A09/A14/A15 as `offline_partial`, not complete.
After the later A10/A11 supplementals it ends at zero `offline_ready`, 35
`offline_partial`, four `live_required`, and 68 `no_capsule`. No live work was
authorized by this batch; its escalation-record ID remains absent.

Remaining unknowns include exact carry/release/collision writers and geometry,
plant eligibility/replacement gates, teardown writers, subtype breadth, and
causal controls. Frame-boundary correlations are not every-cycle attribution.

## Validation

- Capsule preservation: `PASS: 52/52 capsules, 2527165846 external bytes`.
- Derived index: `PASS: rows=3 capsules=3 records=6025`, with the hash above.
- The current queue reports `rows=107 open=91 offline_ready=0
  offline_partial=35 live_required=4 no_capsule=68`; the escalation ledger
  reports two executed entries from the later A10/A11 batch.
- The clean-archive focused Phase-4 suite passed 55 tests. The full safe suite
  run outside the quota-saturated `/tmp` mount passed 660 of 663 selected tests;
  the three remaining failures are the guards that intentionally require a
  literal `/tmp` config or snapshot path. The host account was at its 50,534 MiB
  `/tmp` quota and returned `Errno 122` there, so the path guards could not be
  exercised in this iteration.
- Clean regeneration reports 107 rows, 12 families, and 50/50 generators; the
  exact gate remains correctly open at 16/107 complete with all four exit
  predicates unmet. The Phase-3 evidence inventory reports 29/29 generators,
  30/30 artifacts, and no tracked-input mutations; its remaining open state is
  the inherited retained-live-toolchain environment mismatch set.
- No copyrighted/operator-owned movie, save, capsule, capture, BIOS, token, or
  generated disc bytes entered Git.
