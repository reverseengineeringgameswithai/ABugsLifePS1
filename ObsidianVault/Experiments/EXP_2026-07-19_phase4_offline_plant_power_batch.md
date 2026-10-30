---
type: experiment
status: complete
date: 2026-07-19
system: Phase 4 offline trace analysis
phase: 4
---

# Phase 4 offline plant and player-power batch

This iteration consumed the coherent current rank-1–5 cluster:
`A13_cycle_plant_output`, `B06_invincibility`, `B07_health_power`,
`B08_bubble_shield` and `B09_super_jump`. All five rows remain open. The work
used only control-matched retained frame-boundary capsules and the exact
archived reader; no DuckStation process was launched, no fixture was requested,
and no filename role or frame correlation was promoted into causal ownership.

## Inputs and selection

- The acceptance contract passed its sidecar at SHA-256
  `ee05939d6643dcbee9a62569b78a1523351d5decb6540ee9ac5571d5bebbfc63`.
  Persistent initial context also passed its sidecar at SHA-256
  `5be3a6d98d3ff83520e012a72cda0a02ce70edec9c2cd090ec40d88df3bac578`;
  its 16/107, 91-open, 2/12-family and gate claims were independently
  rederived rather than trusted.
- Recursive inventory found 110 Phase-4 files and 147 broader movie-tree
  files. Sorted relative-path digests were
  `718641d5925272f0b155bf16f634219b45dea618c1400c42b50e795faa222a77`
  and `9908663eea083d41ecdf97f1fcefadc8ebb1fc4ba926eb4719d187f60264e78f`.
  Every consumed movie is paired to its declared start state in the central
  fixture/capsule indexes; movie/state hashes and pristine mounted/save-media
  controls are retained there. Backup bytes and filename semantics were not
  consumed as evidence.
- Capsule preservation passed 50/50 for 2,442,984,379 external bytes. The
  reader is
  `~/Downloads/ABL-external-evidence/duckstation-tools/trace_capsule_query-v1-20260718.py`,
  SHA-256 `b3898f928800efad5a949d1369aa65d786067505e0ed915eec8fdb99f0aa1dde`.
- The pre-selection queue was 16 complete/91 open, with 17
  `offline_ready`, 16 `offline_partial`, six `live_required` and 68
  `no_capsule`. The five selected rows were the open `offline_ready` ranks
  1–5 and joined nine unique capsules, so the whole coherent subsystem cluster
  was taken.

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

python3 tools/phase4_offline_plant_power_batch.py \
  --external-output ~/Downloads/ABL-external-evidence/derived/Phase4/plant-powers-v1/index.json \
  --write
```

The batch retains the queue's exact archived-reader commands, capsule windows
and domains in
`analysis/phase4_offline_plant_power_batch.json#offline_batch.exact_queue_queries`:
40 for A13, 16 for B06, 20 for B07, 16 for B08 and 16 for B09. Each capsule
receives `summary`, full-window `hotspots --top 40`, player/actor/contact RAM,
VRAM and SPU-RAM change queries plus the row-specific plant table or player
power/health query. The generator verifies the reader and capsule-manifest
hashes before reconstructing every record and independently checking the
reader's per-domain hashes.

All 16,785 records were scanned once into the external register/RAM/VRAM/
SPU-RAM/block-flow index. It is 53,952,029 bytes, SHA-256
`daf10dac46dd88cdba54541855ab944d2583f0b5abae749840c1dcb4a6fc9d83`.
Git retains only its generator/schema, preservation hash, bounded summary and
falsifiable tests, not movie/save/capsule or reconstructed frame bytes.

## Observations

### A13 plant-cycle lead

Across blue, brown, green, purple and yellow capsules, 22 zero-to-nonzero slot
type transitions and 20 nonzero-to-zero retirements are retained. Every
creation has a same-boundary one-step cursor increment and exactly one slot
type change. The exact creation frames/types are:

- blue: frames 120/1030/2074/2950, types 7/7/6/7;
- brown: 144/718/1470/1982, types 5/3/8/2;
- green: 199/801/1467/2087, types 4/10/9/1;
- purple: 133/675/1253/1657/1941, types 6/6/6/5/6;
- yellow: 144/1120/1758/2034/2910, types 14/13/11/11/1.

The 20-entry resident selector matrix is constant inside each retained movie
but has two cross-movie variants. Blue/green/purple/yellow share SHA-256
`e81cf16a93aab32481e09f1b559cdad89cb9d4a02cda77e71380a3de4c954b86`;
brown has
`bea914390921740ed74819afc477c4c13da8c5463bd158b7fc6203dc73c20394`.
They differ at entry 11 and entries 16–19. Both capsules are pristine-control
matched. Therefore `0x8007A448` is a runtime-resident table whose observed
contents require fixture/runtime qualification, not one immutable universal
matrix. The capsules do not identify the load/write path or prove all
color/count ownership and lifecycle cases.

### Player-power leads

The four bytes beginning at `0x800A6590` are decoded conservatively as a low
unsigned status halfword and an adjacent raw signed halfword. Treating the
whole range as one `u32` flags value would merge independently changing state.
No semantic name is assigned to the adjacent halfword.

- B06: health stays 4 for all 1,098 records; the low halfword takes 0/2/8 and
  the adjacent raw value spans -30..0. This does not prove invincibility,
  attack ownership, a timer writer or a denial control.
- B07: health changes 3→4 at frame 77 inside a broader low-status-8 interval.
  Player/plant/VRAM/SPU-RAM ranges change on that boundary, but the power
  owner and exact health writer remain unknown.
- B08: health changes 4→3 at frame 277 and 3→2 at frame 381. Both boundaries
  also change the low status halfword 0→2 and adjacent raw value to 45. This
  does not prove bubble ownership, absorption, attack ownership or a
  counterfactual protection result.
- B09: one control movie retains two grounded-to-airborne episodes. Status 0
  takes off at frame 2 with velocity -2816 and reaches Y -16927 at frame 22;
  status 32 takes off at frame 96 with velocity -3520 and reaches Y -26013 at
  frame 122. This is a within-movie frame-boundary correlation, not exact
  enabling-writer attribution.

## Inference and remaining unknowns

The typed A13 boundaries and paired B09 episodes are strong windows for later
ownership/causality work. The A13 matrix comparison also narrows a stale-risk
in the legacy Canon: its address and selection law do not imply cross-fixture
content immutability. These observations remain frame-boundary evidence—not
every-cycle writer, GPU/SPU producer, plant/power owner, attack source or
behavioral-control proof.

A13 still needs selector load/write provenance, full color/count/capacity and
plant interaction/lifecycle controls. B06–B09 still need exact power ownership,
activation/expiration and denial paths, damage/immunity sources, lifecycle and
stage breadth. The regenerated queue therefore derives all five as
`offline_partial`, not complete, and ends at 12 `offline_ready`, 21
`offline_partial`, six `live_required` and 68 `no_capsule`. No live work was
authorized; `analysis/phase4_live_escalations.json` remains valid with zero
entries, so there is no escalation-record ID.

## Validation

- Capsule preservation: `PASS: 50/50 capsules, 2442984379 external bytes`.
- Derived index: `PASS: rows=5 capsules=9 records=16785`, with the hash above.
- Queue after retention: `PASS: rows=107 open=91 offline_ready=12
  offline_partial=21 live_required=6 no_capsule=68`.
- Phase-4 plus knowledge guards: 281 passed.
- The canonical safe runner reached 627 passed/24 failed/51 deselected while
  the candidate was dirty: 20 failures were host `/tmp` quota error 122 and
  four were clean-index Phase-3 freshness guards. Final candidate validation
  therefore uses the same safe marker expression with an external basetemp and
  reruns the cleanliness-sensitive guards after commit.
- The code-only consolidated build passed all four declared layouts and
  produced patched SHA-1 `5936596c576415847b3a7395599e993b36eb7906` when
  `TMPDIR` was moved off the quota-limited `/tmp`; the Vault validator reported
  zero dangling links, evidence-policy errors, dead evidence, duplicate
  addresses, missing aliases or schema errors.

See [[EXP_2026-07-18_phase4_trace_capsules]] for the preservation contract,
[[Seed_plant_output_binding]] for the qualified original-game fact, and
[[Phase 4 - Solve Every Gameplay and Engine Subsystem]] for the binding gate.
