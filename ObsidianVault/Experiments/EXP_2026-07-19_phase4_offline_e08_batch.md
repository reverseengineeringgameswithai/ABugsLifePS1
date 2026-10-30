---
type: experiment
status: complete
date: 2026-07-19
system: Phase 4 E08 authored-source offline batch
phase: 4
---

# Phase 4 offline E08 batch

This iteration consumed every retained capsule relevant to
`E08_props_movers_gates`. E08 remains open. The acceptance sidecar matched
SHA-256 `715f3e51648e781eccea4ff12940ac83363e0a0fa8b73097b38a398bd1e1cad2`;
the persistent context, roadmap, Phase-4 note, capsule experiment, current
107-row queue, and recursive 110/147-file Phase-4/broader movie inventories
were independently revalidated.

## Selection

The pre-analysis queue was 16 complete / 91 open, with zero
`offline_ready`, 42 `offline_partial`, zero `live_required`, and 65
`no_capsule`. E08 was rank 3 and the highest-ranked unconsumed
subsystem-sized partial cluster: 13 relevant capsules and 156 exact scheduled
queries. Rank-1 C16 and rank-2 C15 expose only three and one capsules and have
already been repeatedly deepened. E10 had analyzed this same 13-capsule frame
corpus, making reuse of its derived index mechanically preferable to another
full scan.

`/tmp` had 13 GiB free but the user quota was exhausted; `/var/tmp` had 456
GiB available. No new large scratch was needed. No DuckStation process was
launched and the six-entry escalation ledger remained fully executed with zero
planned entries.

## Exact offline batch

The commands were:

`python3 tools/phase4_offline_contact_batch.py --external-output ~/Downloads/ABL-external-evidence/derived/Phase4/contact-hazard-v1/index.json --check`

`python3 tools/phase4_offline_e08_batch.py --external-index ~/Downloads/ABL-external-evidence/derived/Phase4/contact-hazard-v1/index.json --write`

The first command verifies the shared external index from the exact pinned
reader. The second consumes all 156 queue commands retained verbatim in
`analysis/phase4_offline_e08_batch.json`: per-capsule summaries, full-window
hotspots, player/actor/contact RAM deltas, full VRAM and SPU-RAM change points,
and five E08 typed ranges. Reader SHA-256 is
`b3898f928800efad5a949d1369aa65d786067505e0ed915eec8fdb99f0aa1dde`.

The reused external index is 145,510,233 bytes, SHA-256
`413151a8100bdfac686d0cddea136e53972536b4d797fafe9ced016c1ba065f0`.
It remains external game-derived evidence. Git retains only the consumer,
schema, exact hashes, bounded summaries, and falsification tests.

## Derived findings

All 5,753 reconstructed boundaries and 2,165 actor-event records were
consumed. Their 3,364 individual actor changes all join through live actor
source pointers to measured authored identities. A fixture filename supplies
none of those identities.

Seven of the 28 uncontrolled type-word classes occur in actor changes:
`0x050D`, `0x1B1F`, `0x1E20`, `0x1F04`, `0x2223`, `0x2528`, and `0x2629`.
Five have a bounded HP/flags/source/identity/callback change or a fresh
knockback activation:

- `0x050D`: 13 flag changes on LEVEL05 pit frames 33..111;
- `0x1B1F`: one flag change and five knockback activations on LEVEL11 frames
  132, 290, 346, 428, 502, and 548;
- `0x1E20`: one flag change at LEVEL11 frame 86;
- `0x2528`: flag changes at falling-spikes frame 77 and LEVEL05 pit frame 115;
- `0x2629`: flag changes at falling-spikes frames 61 and 75.

`0x1F04` and `0x2223` show only VM timing/pointer advance changes under this
significance policy. The other 21 uncontrolled type words do not occur in an
actor-change record in this corpus.

At LEVEL11 frames 428 and 548, type `0x1B1F` knockback activates `0 -> 15` on
the same boundaries as player health `1 -> 0` and `0 -> -1`. This makes the
class a high-value native-control lead. It does **not** prove actor-to-player
causality, a hazard role, or E08/E10 ownership. The capsules are frame-boundary
evidence and cannot separate ordered stores inside a frame.

The index independently reproduces the four live typed outcome leaves:
`0x0F06` HP `8 -> 6`/flags `53252 -> 53254` at frame 426; `0x0C13` HP
`6 -> 4`/flags `16449 -> 16451` at 437; `0x060C` HP `999 -> 0` at 343;
and `0x0B11` HP `999 -> 0` at 400. This is a frame-level cross-check, not a
replacement for the retained native controls.

The aggregate passive top blocks begin at `0x80064A70`, `0x80014170`,
`0x80014180`, `0x80014194`, and `0x80072894`. They come only from the
per-frame top-block retention and cannot establish an exact writer or complete
execution path.

## Decision and remaining frontier

No class owner, native control, campaign row, or family is promoted. The
native-control partition remains 19/28. Authored switch/gate/mover state,
denial/success rules, exact writers, and checkpoint/death/reload/transition/
save-load behavior remain open. A future live experiment must first declare a
specific positive/negative control for a prioritized class in the generated
escalation ledger; this offline iteration does not authorize one.

After registration the queue remains zero `offline_ready`, 42
`offline_partial`, zero `live_required`, and 65 `no_capsule`. It still has 107
unique rows, 16 complete / 91 open. No Phase-4 exit predicate changes.

Machine evidence: `analysis/phase4_offline_e08_batch.json`. Campaign:
[[Game Solving Campaign - Props Movers Switches and Gates]]. Canon handoff:
[[SYS_pass_table_props_and_movers]].
