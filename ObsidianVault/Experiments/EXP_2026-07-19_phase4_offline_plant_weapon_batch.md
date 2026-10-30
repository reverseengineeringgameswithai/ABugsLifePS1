---
type: experiment
status: complete
date: 2026-07-19
system: Phase 4 offline trace analysis
phase: 4
---

# Phase 4 offline yellow-plant weapon batch

This iteration consumed the coherent current rank-1–3 cluster:
`B11_blue_berry_shooter`, `B12_homing_shooter`, and `B13_mine_plant`.
All three rows remain open. The work used only control-matched retained
frame-boundary capsules and the exact archived reader; no DuckStation process
was launched, no fixture was requested, and no filename role or same-frame
correlation was promoted into causal ownership.

## Inputs and selection

- The acceptance contract passed its SHA-256 sidecar at
  `ee05939d6643dcbee9a62569b78a1523351d5decb6540ee9ac5571d5bebbfc63`.
  Persistent initial context passed its sidecar at
  `5be3a6d98d3ff83520e012a72cda0a02ce70edec9c2cd090ec40d88df3bac578`;
  its closure claims were independently rederived rather than trusted.
- Recursive inventory found 110 Phase-4 files and 147 broader movie-tree
  files. Sorted relative-path digests remained
  `718641d5925272f0b155bf16f634219b45dea618c1400c42b50e795faa222a77`
  and `9908663eea083d41ecdf97f1fcefadc8ebb1fc4ba926eb4719d187f60264e78f`.
  Every consumed movie is paired to its declared start state and pristine
  mounted/save-media control in the central fixture/capsule indexes; backup
  bytes and filename semantics were not consumed as evidence.
- Capsule preservation passed 50/50 for 2,442,984,379 external bytes. The
  reader is
  `~/Downloads/ABL-external-evidence/duckstation-tools/trace_capsule_query-v1-20260718.py`,
  SHA-256 `b3898f928800efad5a949d1369aa65d786067505e0ed915eec8fdb99f0aa1dde`.
- The pre-selection queue was 16 complete/91 open, with 12
  `offline_ready`, 21 `offline_partial`, six `live_required`, and 68
  `no_capsule`. The selected rows were its three highest-ranked open
  `offline_ready` rows and joined four unique capsules: the shared A13 yellow
  trace plus the dedicated B11, B12, and B13 traces.

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

python3 tools/phase4_offline_plant_weapon_batch.py \
  --external-output ~/Downloads/ABL-external-evidence/derived/Phase4/plant-weapons-v1/index.json \
  --write
```

The tracked summary retains all 48 exact queue commands—16 per row—in
`analysis/phase4_offline_plant_weapon_batch.json#offline_batch.exact_queue_queries`.
For each relevant capsule these cover `summary`, full-window
`hotspots --top 40`, player/actor/contact RAM, full VRAM and SPU-RAM changes,
and the row-specific plant jump-table or quota range. The generator verifies
reader and capsule-manifest hashes, reconstructs every frame record, and
independently checks the reader's per-domain hashes.

All 5,830 records were scanned once into the external register/RAM/VRAM/
SPU-RAM/block-flow index. It is 102,510,132 bytes, SHA-256
`15912c032fe7c648f10d6da4498a7d2d2233b71f74546316e7b0534831e77631`.
Git retains only its generator/source contract, preservation hash, bounded
summary, and falsifiable tests—not movie, save, capsule, or reconstructed frame
bytes.

## Observations

### B11 type-14 shooter lead

The dedicated B11 capsule creates plant type 14 in slot 0 at movie frame 42;
it remains present through the retained endpoint. Enemy quota remains 9. At
frame 398 actor slot 0/id 37 changes HP 2→999 while an allocator-occupied
contact has action 2, raw `u16 +0x24 == 110`, kind 0, flags 229, lifetime 1,
and state 20. Plant, actor, contact, VRAM, and SPU-RAM ranges all change at that
boundary; quota does not. The same actor changes HP 999→0 at frame 448.

This precisely indexes a typed same-frame signature. It does not establish
that raw field 110 is a model ID, that the contact is owned by the plant, or
that it wrote the HP transition.

### B12 type-13 shooter lead

The dedicated B12 capsule creates plant type 13 in slot 1 at frame 288; it
remains present through the retained endpoint. Enemy quota remains 26. Actor
slot 26/id 17 changes HP 1→999 at frame 668 and 999→0 at 716; actor slot 6/id
18 changes 3→999 at frame 1216 and 999→0 at 1218. At the 668 and 1216
boundaries, an allocator-occupied contact has action 2, raw
`u16 +0x24 == 124`, kind 0, flags 237, and lifetime 1. The relevant RAM, VRAM,
and SPU-RAM ranges change while quota does not.

The retained trajectories and raw signature are useful homing/target-selection
leads, but passive frame boundaries do not prove either behavior, ownership,
or the exact HP writer.

### B13 type-11 mine contrast

The shared yellow capsule retains two type-11 episodes:

- slot 5 is created at frame 1758; frame 1848 joins quota 15→14 and actor
  slot 10/id 9 HP 2→999; the plant retires at frame 1852;
- slot 6 is created at frame 2034 and retires at frame 2518 without any quota
  boundary.

The dedicated B13 capsule retains no type-11 plant, quota boundary, or actor-HP
boundary. It is therefore a negative observation in the available frame
domain, not a mine-trigger fixture forced from its filename. The two shared
episodes provide a within-movie quota-changing/no-quota-change contrast, but
do not identify a fuse, proximity rule, enemy ownership, collision callback,
permanent-kill path, or causal writer.

## Inference and remaining unknowns

The distinct type-14/raw-110 and type-13/raw-124 correlations, plus the paired
type-11 episode contrast, are bounded windows for later writer and behavioral
controls. They do not establish exact CPU writers, contact ownership, target
selection, collision/fuse laws, DMA/GPU/SPU producers, stage breadth, or full
activation/expiration lifecycle.

The regenerated queue therefore derives these three rows as
`offline_partial`, not complete, and ends at nine `offline_ready`, 24
`offline_partial`, six `live_required`, and 68 `no_capsule`. The new current
ranks begin A09, A14, A15, B01, and B02. No live work was authorized;
`analysis/phase4_live_escalations.json` remains valid with zero entries, so
there is no escalation-record ID.

## Validation

- Capsule preservation: `PASS: 50/50 capsules, 2442984379 external bytes`.
- Derived index: `PASS: rows=3 capsules=4 records=5830`, with the hash above.
- Queue after retention: `PASS: rows=107 open=91 offline_ready=9
  offline_partial=24 live_required=6 no_capsule=68`.
- Phase-4 plus knowledge guards: 287 passed.
- The canonical safe selection reached 633 passed/24 failed/51 deselected
  while the candidate was dirty. An external-basetemp retry passed 19 of the
  failures; three isolation guards require literal `/tmp` paths and remained
  unexecutable under host quota error 122, while the remaining two were
  cleanliness-sensitive Phase-3 ledger/inventory checks reserved for the
  committed candidate.
- The code-only consolidated build passed all four declared layouts and
  produced patched SHA-1 `5936596c576415847b3a7395599e993b36eb7906`; the
  Vault validator reported zero dangling links, evidence-policy errors, dead
  evidence, duplicate addresses, missing aliases, or schema errors.

See [[EXP_2026-07-18_phase4_trace_capsules]] for the preservation contract,
[[SYS_seed_plant_behaviors]] for bounded original-game Canon, and
[[Phase 4 - Solve Every Gameplay and Engine Subsystem]] for the binding gate.
