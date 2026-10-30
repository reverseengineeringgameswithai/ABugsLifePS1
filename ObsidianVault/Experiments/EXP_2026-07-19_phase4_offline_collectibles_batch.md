---
type: experiment
status: complete
date: 2026-07-19
system: Phase 4 offline trace analysis
phase: 4
---

# Phase 4 offline collectibles and equipment batch

This iteration consumed all four rows in the highest-ranked coherent
collectibles/equipment cluster: `C01_grain_pickup`,
`C02_fifty_grain_reward`, `C13_grain_harvester` and `C14_telescope`. It used
only the retained frame-boundary capsules and exact archived reader. No
DuckStation process was launched, no fixture was requested, no filename role
was promoted, and no campaign row was closed.

## Inputs and selection

- The acceptance-contract sidecar passed at SHA-256
  `ee05939d6643dcbee9a62569b78a1523351d5decb6540ee9ac5571d5bebbfc63`.
- Recursive inventory again found 110 Phase-4 files (50 movies, 50 paired
  start states and ten backups) and 147 broader movie-tree files. Every
  capsule-consumed movie/state remains centrally hash-, size-, consumer- and
  pristine-media-declared; backup bytes remain unconsumed.
- The 50/50 capsule preservation check passed for 2,442,984,379 external
  bytes. The reader is
  `~/Downloads/ABL-external-evidence/duckstation-tools/trace_capsule_query-v1-20260718.py`,
  SHA-256 `b3898f928800efad5a949d1369aa65d786067505e0ed915eec8fdb99f0aa1dde`.
- The pre-selection queue was 16 complete/91 open, with 21
  `offline_ready`, 12 `offline_partial`, six `live_required` and 68
  `no_capsule`. C01, C02, C13 and C14 were open `offline_ready` ranks 1–4;
  taking the whole coherent cluster exceeded the three-row minimum.

## Offline commands

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

python3 tools/phase4_offline_collectibles_batch.py \
  --external-output ~/Downloads/ABL-external-evidence/derived/Phase4/collectibles-v1/index.json \
  --write
```

For each of the four capsules, the retained batch runs the queue's exact
archived-reader `summary`, full-window `hotspots --top 40`, RAM `changes` for
the player block (`0xA6500+0xB0`), actor pool (`0x9FD80+0x2100`) and contact
pool (`0xB0D18+0xE00`), full VRAM (`0+0x100000`) and SPU-RAM
(`0+0x80000`). It also runs the row-specific typed query: grain
`0xA65A1+4` for C01/C13; true health `0xA6594+4`, grain and display health
`0xA7E2A+4` for C02; and object-pointer-list entry `0x96B98+4` for C14.
`analysis/phase4_offline_collectibles_batch.json` retains all 34 concrete
absolute commands, capsule windows and hashes in `exact_queue_queries`.

The generator verifies the reader hash before loading it, reconstructs all
2,354 records, and writes the repeated per-frame register/RAM/VRAM/SPU-RAM/
block-flow work once to the external index. Its preservation SHA-256 is
`e848f907fc5ac72da22f456fd838275b28da8df0c2b892071e8b0c5f2cf89d74`
for 38,561,548 bytes. Git retains the generator, schema, bounded findings,
hash manifest and tests, not those game-derived frame records.

## Observations

### C01 grain lead

The grain byte changes `10 -> 11` at movie frame 196 and `11 -> 12` at frame
540. Both frames intersect player, actor and contact RAM ranges plus VRAM and
SPU-RAM change points. At each boundary exactly five contact records change
from gate zero to positive gates with action 4, radius 100, state 0 and flags
32. No active filtered contact or actor-HP transition identifies the pickup
owner.

### C02 fifty-grain lead

Grain changes `49 -> 50` at frame 160. True health remains `4 -> 4`; the frame
intersects player/actor/contact RAM and VRAM changes but has no SPU-RAM change.
Five action-4/radius-100 effect records again reset from gate zero. The display
field cycles through 0..7 throughout the movie (218 changes) and steps `1 ->
2` on frame 160, so that display animation cannot establish a heal.

### C13 harvester lead

Nine grain increments occur at frames 211, 227, 247, 281, 339, 485, 507, 535
and 561, taking grain `0 -> 9`. Each boundary intersects all five retained
change domains and has exactly one action-20 contact record change from state
22/gate greater than one to state 16/gate one. The one-for-one correlation is
repeatable; the filename does not prove that the harvester owns those records
or the grain writer.

### C14 telescope lead

Health/lives/grain do not change. Manual camera mode remains zero; distance
900, orbit yaw 2454, profile/suppression 1, pitch scale 32, vertical angle 0,
orbit bias 0 and vertical target 12288 remain constant. The queried first
object descriptor pointer remains `0x80081D98`. At frame 65 the derived target
changes from `[-1192,-66136,480308]` to `[-1360,-65770,481441]`; derived
position then changes every two frames through frame 147, ending at
`[-1360,-65777,481434]`. This bounds a camera transition in the named movie;
it does not identify a telescope owner or camera producer.

## Inference and remaining unknowns

The repeated C01/C02 five-record signature and C13 one-for-one action-20
signature are useful event-window discriminators. They remain frame-boundary
correlations, not exact CPU writer, actor/fixture ownership, GPU/SPU producer
or native-control evidence. C02's full-health fixture specifically does not
test a heal. C14 likewise shows that the transition is not the resident manual
mode/input path, but not which scripted object owns it.

The rows therefore remain open. C01/C02 still need reward-owner/writer,
capacity/denial and lifecycle controls; C13 needs harvester ownership, range,
capacity and lifecycle breadth; C14 needs object/camera ownership, interaction
conditions and lifecycle. Those named gaps can use this external index before
any narrowly justified live experiment.

The regenerated queue derives the four rows as `offline_partial`, not
complete. Counts are now 17 `offline_ready`, 16 `offline_partial`, six
`live_required` and 68 `no_capsule`; ranks 1–5 advance to A13, B06, B07, B08
and B09. `analysis/phase4_live_escalations.json` has zero entries, so there is
no escalation-record ID.

## Validation

- Capsule preservation: `PASS: 50/50 capsules, 2442984379 external bytes`.
- Derived index: `PASS: rows=4 capsules=4 records=2354`, with the hash above.
- Queue: `PASS: rows=107 open=91 offline_ready=17 offline_partial=16
  live_required=6 no_capsule=68`.
- Live ledger: `PASS: 0 live escalation entries`.
- Focused generator/scheduler guards: 14 passed.

See [[EXP_2026-07-18_phase4_trace_capsules]] for the preservation boundary and
[[Phase 4 - Solve Every Gameplay and Engine Subsystem]] for the binding gate.
