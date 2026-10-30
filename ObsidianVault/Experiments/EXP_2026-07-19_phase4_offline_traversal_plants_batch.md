---
type: experiment
status: complete
date: 2026-07-19
system: Phase 4 offline trace analysis
phase: 4
---

# Phase 4 offline traversal-plant batch

Iteration 6 consumed the complete coherent current rank-1–6 cluster:
`B01_mushroom_trampoline`, `B02_propeller_plant`, `B03_dandelion_glide`,
`B04_cannon_plant`, `B05_green_leaf_platforms`, and
`B10_purple_berry_plants`. All six rows remain open. The work used only
pristine-control-matched retained frame-boundary capsules and the exact
archived reader. No DuckStation process was launched and no fixture was
requested.

## Inputs and selection

- The acceptance contract and persistent context passed their SHA-256
  sidecars: `ee05939d6643dcbee9a62569b78a1523351d5decb6540ee9ac5571d5bebbfc63`
  and `5be3a6b21556fae56afe1d3ae509200e6eecdacc01d1e1be25fbf92a8057e5b6`.
- Recursive inventory found 110 Phase-4 files and 147 broader movie-tree
  files. Each selected movie/save pair is centrally hash/size/media-class
  declared, and its capsule independently matches pristine mounted/save
  media. Filenames and JSON serial strings were not treated as media proof.
- Capsule preservation passed 50/50 for 2,442,984,379 external bytes. The
  exact reader is
  `~/Downloads/ABL-external-evidence/duckstation-tools/trace_capsule_query-v1-20260718.py`,
  SHA-256 `b3898f928800efad5a949d1369aa65d786067505e0ed915eec8fdb99f0aa1dde`.
- The pre-selection queue was 16 complete/91 open, with six
  `offline_ready`, 27 `offline_partial`, six `live_required`, and 68
  `no_capsule`. The selected rows were all remaining `offline_ready` work and
  joined six unique capsules.

## Offline commands and preservation

```bash
python3 tools/phase4_offline_queue.py \
  --movie-root ~/Downloads/ABL/movies --inventory-only --write

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

python3 tools/phase4_offline_traversal_plants_batch.py \
  --external-output ~/Downloads/ABL-external-evidence/derived/Phase4/traversal-plants-v1/index.json \
  --write
```

The tracked summary retains the 43 exact queue queries: seven for each of
B01–B05 and eight for B10. They include every full-capsule summary/hotspot
scan plus player, actor, contact, VRAM, SPU-RAM, and B10 equipped-byte windows.
The generator independently scans the same domains with the pinned reader and
verifies movie bytes, declared start states, capsule manifests, record counts,
and source dependencies.

All 8,572 records were reconstructed once into the external register/RAM/
VRAM/SPU-RAM/block-flow index. It is 58,047,074 bytes, SHA-256
`96884a7373430b3b1431bd3b52eb004531c8e894d2adc89d19b3afb36868e99d`.
Git retains only the generator, source contract, preservation hash, bounded
summary, and falsifiable tests—not movie, save, capsule, reconstructed-frame,
or generated-disc bytes.

## Observations

### B01 mushroom trampoline

Player vertical velocity changes to `-3328` at movie frames 207, 335, 385,
and 435. At each boundary, state is 5, grounded is zero, the passive
`0x8005C58C` block starts five times, and the nearest type-5 plant has state 2.
Those nearest plants occupy four distinct slots: 6, 5, 4, and 2. This is a
four-bounce chain observation; it does not establish a fifth-bounce bonus,
general combo law, collision primitive, or exact writer.

### B02 propeller lift and the seed boundary

Two player state-5 lift runs span frames 61–82 and 525–546. Each steps through
stored vertical velocities `-2048`, `-2304`, `-2560`, `-2816`, and `-3072`,
then retains the `-3072` minimum. Seed actor slot 26 (`0x800A0AE8`) satisfies
the exact player-position attachment predicate over frames 441–476. It then
continues a vertical trajectory through frame 530, reaching stored velocity
`-3584` and Y `-149214`. The attachment ends 49 frames before the second lift
begins. This bounds the player lift and seed sequence but does not prove that
the propeller caused the seed trajectory.

### B03 dandelion and later handler overlap

At frame 180, player vertical velocity changes from `+1856` to `-4096` with
state 5 and grounded zero. Passive dandelion and propeller handler starts
overlap over 42 retained frames from 914 through 996; the first later grounded
zero-velocity boundary is frame 974. This does not identify glide attachment,
per-frame sink, steering, an updraft trigger, or an exact writer.

### B04 cannon/dandelion movie-name limit

The launch-associated constant seated interval is frames 121–152. Frame 153
has vertical velocity `-7936` with one cannon and one dandelion handler block
start. No later discrete transition to `-4096` is retained. The fixture proves
one cannon-sized launch while both handlers coexist; its filename is not proof
that a cannon-to-dandelion combo succeeded.

### B05 four green lifecycle paths

The green fixture retains four complete slot lifecycles:

| Type | Slot | Creation | Retirement | Retained lifetime | Phase boundaries |
|---:|---:|---:|---:|---:|---|
| 4 | 3 | 199 | 551 | 352 | 0→5→7→69→5 |
| 10 | 4 | 801 | 1187 | 386 | 0→5→7→69→5 |
| 9 | 5 | 1467 | 2015 | 548 | 0→5→7→69→5 |
| 1 | 6 | 2087 | 2645 | 558 | 0→5→7→69→5 |

The shared `0x8005CCE8` tail starts 27,140 times. That whole-walker block-flow
count does not bind an execution to a specific leaf, collision plane, height,
or climb primitive.

### B10 purple berry grants

Four complete type-6 lifecycles begin/end at 133/437, 675/989, 1253/1635,
and 1941/2243. The equipped byte at `0x800A6597` changes `0→1→2→4→3` at
frames 253, 777, 1343, and 2061. At each same boundary the matching statically
identified grant-handler block starts once. Creation-to-equip gaps are
120/102/90/120 frames. This confirms the retained tier/equip sequence, not the
exact pickup collision, writer instruction, reset law, or whole-game breadth.

## Decision and remaining unknowns

The regenerated queue derives all six rows as `offline_partial`, not complete,
and ends at zero `offline_ready`, 33 `offline_partial`, six `live_required`,
and 68 `no_capsule`. No live work was authorized;
`analysis/phase4_live_escalations.json` remains valid with zero entries, so
there is no escalation-record ID.

Named unknowns remain the exact collision/velocity/equip writers, combo and
glide/updraft laws, collision geometry, steering and animation/audio behavior,
green leaf planes/climb primitives, purple reset behavior, causal controls,
and applicable stage/lifecycle breadth. Frame-boundary correlations and
passive block starts are not every-cycle attribution.

## Validation

- Capsule preservation: `PASS: 50/50 capsules, 2442984379 external bytes`.
- Derived index: `PASS: rows=6 capsules=6 records=8572`, with the hash above.
- The focused queue/batch/gate/source-dependency suite passed 89 tests. The
  generator reproduced the exact external bytes and tracked summary under
  `--check` after the queue moved the rows to `offline_partial`.
- The mandated safe wrapper selected 671 tests and reported `651 passed, 20
  failed, 51 deselected in 277.72s`. The host account is at its 50,534 MiB
  `/tmp` quota; the 20 allocation-dependent failures were quota effects
  (`Errno 122`) while creating fixtures or their outputs. Re-running the same
  selection with an isolated `/var/tmp` base reported `668 passed, 3 failed,
  51 deselected in 278.21s`; the only three failures are guards that
  deliberately require their config or toolchain snapshot to reside under
  literal `/tmp`.
- A `git archive` of tested HEAD provisioned and then reverified all 1,362
  centrally declared external inputs. It reproduced the 327/327 build-input
  identity, Phase-3 audit bytes with `tracked_input_mutations=[]`, the queue,
  batch index, empty escalation ledger, 51/51 Phase-4 generator inventory, and
  exact nonzero Phase-4 gate. Its focused queue/batch/gate/capsule/vault suite
  passed 42 tests.
- The default hook/cave declaration validator accepted
  `blackberry,golddrop,grain_hud`; build identity passed 327/327 staged inputs.
- The final queue reports `rows=107 open=91 offline_ready=0
  offline_partial=33 live_required=6 no_capsule=68`; the live-escalation
  ledger reports zero entries.
- No copyrighted/operator-owned movie, save, capsule, capture, BIOS, token,
  credential, or generated disc bytes entered Git.
