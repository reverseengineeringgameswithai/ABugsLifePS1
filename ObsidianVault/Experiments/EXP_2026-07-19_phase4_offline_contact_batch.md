---
type: experiment
status: complete
date: 2026-07-19
system: Phase 4 offline trace analysis
phase: 4
---

# Phase 4 offline contact and hazard batch

This iteration converted the retained capsule set into the authoritative 107-row
offline opportunity queue, then consumed the current five highest-priority open
`offline_ready` rows as one contact/hazard batch. It did not launch DuckStation,
request a fixture, promote a filename role, or close a campaign.

## Inputs and authority

- The acceptance contract SHA-256 sidecar passed with
  `ee05939d6643dcbee9a62569b78a1523351d5decb6540ee9ac5571d5bebbfc63`.
- Recursive inventory found 110 files under `movies/Phase4` (50 movies, 50
  start states and 10 backups) and 147 files in the broader movie tree (78
  movies, 56 start states and 12 backups). The broader tree SHA-256 is
  `41d16a5367cecf88cfcec98ed392d462f8d5977b7a5679c8c920a1167679d21a`.
- All 100 movie/save files consumed by the capsule set join current central
  hash, size, consumer and pristine-media declarations. The twelve undeclared
  files are backups and none is consumed. A movie JSON serial remains metadata,
  not media proof.
- The exact archived reader is
  `~/Downloads/ABL-external-evidence/duckstation-tools/trace_capsule_query-v1-20260718.py`,
  SHA-256 `b3898f928800efad5a949d1369aa65d786067505e0ed915eec8fdb99f0aa1dde`.
  The v2 capsule validator reproduced 50/50 complete, control-matched capsules
  and 2,442,984,379 preserved external bytes against the byte-identical v1
  comparison.

## Commands

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

python3 tools/phase4_offline_contact_batch.py \
  --external-output ~/Downloads/ABL-external-evidence/derived/Phase4/contact-hazard-v1/index.json \
  --write
```

The queue exposes every concrete archived-reader `summary`, full-window
`hotspots`, player/actor/contact RAM `changes`, full-VRAM `changes`, full-SPU-RAM
`changes`, and row-specific typed-range query. The batch generator loads that
same reader only after verifying its hash, reconstructs every frame once, and
materializes the repeated cross-movie queries in one external index.

## Queue decision

Low-level coverage derivation reports 16 complete and 91 open rows. The
selection-time snapshot derived exactly one classification for every one of 107
unique rows:

| Classification | Count |
|---|---:|
| `offline_ready` | 26 |
| `offline_partial` | 7 |
| `live_required` | 6 |
| `no_capsule` | 68 |

The selected rows are queue ranks 1–5: `E10_hazards`, `D11_mites_grubs`,
`D08_flies`, `D09_cockroaches`, and `D15_daddy_long_legs`. They cover all 13
relevant capsules. Active partial rows C16, C15, E08 and E15 rank below this
new open batch, so no load-bearing dependency justified returning to them.

After retaining and revalidating the batch, the authoritative queue advances
these five rows to `offline_partial` from the artifact's source, reader,
capsule and external-index hashes—not from an authored completion flag. The
current counts are therefore 21 `offline_ready`, 12 `offline_partial`, six
`live_required` and 68 `no_capsule`. Its new ranks 1–5 are
`C01_grain_pickup`, `C02_fifty_grain_reward`, `C13_grain_harvester`,
`C14_telescope` and `A13_cycle_plant_output`, preventing the next iteration
from silently repeating this batch.

The generator and guards recompute completion from coverage evidence and reject
a row count other than 107, omitted or duplicate row IDs, stale input hashes,
invalid classifications, count mismatches, and authored `pass`, `passes`,
`complete`, `completed`, `gate_met`, `status_pass`, `verified` or `solved`
fields. `analysis/phase4_live_escalations.json` contains zero entries; no live
run was authorized or needed.

## Observation

The external index reconstructs 5,753 frame records across 13 capsules and
retains register hashes, RAM/VRAM/SPU-RAM hashes and change points, typed player,
64-slot actor and 64-slot contact records, plus per-frame and full-window block
hotspots. SHA-256 is
`413151a8100bdfac686d0cddea136e53972536b4d797fafe9ced016c1ba065f0`
for 145,510,233 bytes. It is game-derived evidence outside Git; the tracked
artifact is only its schema, preservation manifest, bounded summary and tests.

Frame-boundary player outcomes are:

- D08-named lead: health `4 -> 3` at movie frame 190.
- D11 grub-named lead: health `4 -> 3` at frame 201; mite-named lead:
  health `4 -> 3` at frame 111.
- E10-named leads: acorn frames 428 (`1 -> 0`) and 548 (`0 -> -1`);
  falling-rock frame 331 (`4 -> 3`); falling-spike frame 105 (`1 -> 0`);
  goo frames 108 (`4 -> 3`) and 198 (`3 -> 2`); ground-bird frame 488
  lives `4 -> 3`; pit LEVEL02 frame 157 health/lives `3/5 -> 4/4`;
  pit LEVEL05 frame 145 `0/1 -> 4/0`; and pit LEVEL07 frame 205 lives
  `6 -> 5`.
- The D09- and D15-named windows have no player health/lives delta. They do
  retain two and three actor-HP field changes respectively; D15 also has 85
  typed contact-pool change frames. This does not identify the named species.

In aggregate the batch retains 11 health changes, four life changes, 12 actor-HP
field changes and 29 numeric actor IDs. Every health-change frame also intersects
the player block, actor pool, contact pool, VRAM and SPU-RAM change domains.

## Inference and non-promotion boundary

The batch confirms and indexes the earlier bounded player-outcome observations
from the E08 hazard/contact work at exact capsule frame boundaries. It adds a
reusable cross-movie change/hotspot surface; it does not turn those prior leads
into species or hazard ownership.

Same-frame intersection is weak correlation because the selected windows change
all five domains frequently. It does not identify an exact CPU writer,
DMA/GPU/SPU producer, attack source, actor owner or causal control. Numeric actor
IDs are fixed-pool observations, not D-row identities, and filenames remain
leads only. Therefore no Canon fact, campaign status, family count or acceptance
row changes.

Named next unknowns are hazard kind/producer ownership and stage breadth for
E10; actor/species ownership, AI, attacks, drops and lifecycle for D08/D09/D11;
and web projectile/range/motion/collision ownership for D15. Those questions can
consume the external index before any narrowly predeclared live control.

## Validation

- Capsule preservation: `PASS: 50/50 capsules, 2442984379 external bytes`.
- Queue: `PASS: rows=107 open=91 offline_ready=21 offline_partial=12
  live_required=6 no_capsule=68`.
- Derived index: `PASS: rows=5 capsules=13 records=5753` with the hash above.
- Focused scheduler/index guards: 11 passed.

See [[EXP_2026-07-18_phase4_trace_capsules]] for the preservation contract and
[[Phase 4 - Solve Every Gameplay and Engine Subsystem]] for the binding gate.
