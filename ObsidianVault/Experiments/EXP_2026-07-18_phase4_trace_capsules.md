---
type: experiment
status: complete
date: 2026-07-18
system: DuckStation external debugger
phase: 4
---

# Phase 4 persistent trace capsules

This experiment records each hash-pinned movie under `movies/Phase4` once into an external, offline-queryable
DuckStation trace capsule. Its purpose is to let future RE sessions correlate registers, RAM/VRAM/SPU changes, and
executed block hotspots with movie frames using scripts, without repeatedly reloading and replaying the movie.

## Authority and scope

- Behavioral authority is the hash-verified pristine SCUS-94288 retail image. ALLMODS is not an input.
- Each accepted capsule is frame-exact for all 103 debugger-visible CPU/COP0/GTE registers, main RAM, VRAM, and SPU RAM;
  it also retains periodic flat full-machine checkpoints and a passive basic-block-start histogram per frame.
- This is not an every-hardware-cycle dump. Exact writer/DMA/GPU/SPU attribution still requires a targeted experiment
  after the capsule narrows the relevant frame window.
- Movies, saves, chunks, checkpoints, and tokens remain external copyrighted/game-derived evidence. The repository
  retains only hashes, roles, validation results, commands, schemas, and this handoff.

## Collection and consumption

DuckStation contract: `~/duckstation/docs/external-debugger-trace-capsules.md`.

Final external set: `~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v2`.

Independent rehearsal set: `~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v1`.

Central validator/index:

```bash
python3 tools/phase4_trace_capsules.py \
  --movie-root ~/Downloads/ABL/movies/Phase4 \
  --capsule-root ~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v2 \
  --comparison-root ~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v1 \
  --require-byte-identical-comparison \
  --binary-snapshot ~/Downloads/ABL-external-evidence/duckstation-binaries/duckstation-qt-trace-capsule-v1-20260718 \
  --offline-reader-snapshot ~/Downloads/ABL-external-evidence/duckstation-tools/trace_capsule_query-v1-20260718.py \
  --write
```

Offline examples:

```bash
QUERY=~/duckstation/scripts/debugger-client/trace_capsule_query.py
python3 "$QUERY" <capsule-directory> summary
python3 "$QUERY" <capsule-directory> changes --domain ram --offset 0xa6590 --length 4
python3 "$QUERY" <capsule-directory> hotspots --start 100 --end 300 --top 40
```

## Result

The collection is complete: 50/50 current Phase-4 movies, 50,052 movie frames, and 2,442,984,379 externally retained
capsule bytes. Every capsule is hash-valid, non-truncated, independently control-matched, and bound to pristine media,
the exact running DuckStation binary, and the archived source tree. The final collection manifest is SHA-256
`be545ed322878f47a55dd38e8e354bd2afcd0c36f43ae5c3716196a1bbb7da2b`.

The independent rehearsal and final runs reproduced all 50/50 frame-domain chunk sets byte-for-byte. Flat checkpoint
blobs differed across the two isolated profiles: DuckStation records bounded profile/memory-card serialization state in
the flat save, and logged that the state card differed from the fresh profile card. This does not weaken the stable
offline domains—RAM, VRAM, SPU RAM, all registers, and block-flow chunks were identical—but it means checkpoint files
must be treated as exact run-local resume evidence, not as a cross-profile canonical serialization.

The exact running binary is retained externally at
`~/Downloads/ABL-external-evidence/duckstation-binaries/duckstation-qt-trace-capsule-v1-20260718`
(SHA-256 `55d589032641ad0904526742f2209c034a710a162ebba3e1bc04b4c5da6075a8`). The source snapshot is retained at
`~/Downloads/ABL-external-evidence/duckstation-source/duckstation-trace-capsule-v1-20260718.tar.zst`
(SHA-256 `ad56dcf51d6021d691045f081e2c3af39728c831e158371a868255527282822d`).

### Runnable preservation correction — 2026-07-19

The single executable above is identity evidence but is not a runnable app-root by
itself: DuckStation resolves `resources/`, translations, and companion shared libraries
relative to its executable. Launching the relocated descriptive filename also exposed a
launcher defect that compared Linux's truncated process name to the literal
`duckstation-qt`; it falsely reported an exit while the isolated process remained live.

The runnable external bundle is now:

`~/Downloads/ABL-external-evidence/duckstation-runtimes/trace-capsule-v1-20260718/duckstation-qt`

Its executable retains SHA-256
`55d589032641ad0904526742f2209c034a710a162ebba3e1bc04b4c5da6075a8`.
`SHA256SUMS` covers 207 runtime files / 140,212,131 bytes and has SHA-256
`1c1c6923e455ba35b888016efe58186018c21013b035259438a8eb13f6ed1228`.
The repaired isolated launcher accepts the complete bundle, reports API 2.1.0 with 208
methods, verifies mounted `SCUS-94288`, and stops the owned PID; it rejects the lone
executable before spawning. Future capsule collection must validate this manifest and
record the runtime `debugger.capabilities` binary hash. The central capsule generator
still needs to promote this bundle/manifest into its machine-readable preservation
index; that is explicit opening work, not silently implied by this note.

A green capsule is reusable evidence, not by itself a solved Phase-4 campaign row; semantic conclusions still require
promotion into the relevant Canon and machine layers.

Going forward, this is the first evidence lane for every Phase-4 iteration. Validate the index and analyze the relevant
movie capsule offline before launching DuckStation. Live API work remains necessary for exact writer/DMA/GPU/SPU
causality and new behavioral controls, but the campaign note must state which missing capsule domain required that
escalation.

## Substantial offline queue contract

Future iterations must not satisfy “capsule first” with one summary query. The generated
`analysis/phase4_offline_opportunity_queue.json` joins every one of the 107 campaign rows
to retained movie/capsule hashes, available domains, exact offline batch queries,
answerable assertions, dependencies, priority, and a derived classification of
`offline_ready`, `offline_partial`, `live_required`, or `no_capsule`. An iteration takes
one coherent subsystem cluster or normally at least three highest-value open
`offline_ready` rows. The queue's generator/guards reject omissions, duplicates, stale
source hashes, and trusted high-level completion flags.

Any live escalation is predeclared in generated
`analysis/phase4_live_escalations.json`, including every relevant capsule query already
run, the exact missing information, planned native control, expected evidence, and the
load-bearing/priority reason another offline batch does not come first. Generic
causality wording or retrospective justification fails the contract. Repeated
cross-movie analysis should be materialized as an externally preserved derived index;
only its reproducible tooling, schema, manifest/hashes, summaries, and tests are tracked.

## Validation

- Final preservation-index regeneration and freshness check: PASS, 50/50 capsules, 2,442,984,379 external bytes,
  zero errors.
- Independent reproduction: 50/50 frame-domain chunk sets byte-identical; no mismatches.
- Pristine build identity: `tools/build_identity.py --verify` PASS, 327/327 staged inputs matched pins.
- Offline reader: two reconstruction/corruption guards passed; direct `summary`, `changes`, and `hotspots` queries ran
  against the final A09 capsule with no DuckStation process active.
- DuckStation: Release target current, core test 1/1 passed, Python compilation passed, and `git diff --check` passed
  apart from the repository's informational Visual Studio CRLF warning.
- Vault validation: zero dangling links, evidence-policy violations, dead evidence files, duplicate addresses, missing
  aliases, or schema errors.
- Capsule contract guards: 2/2 passed. The broader dirty-worktree safe suite was not globally green: 410 passed and 18
  failed in pre-existing terrain and Phase-0–3 freshness/gate areas; the capsule guards themselves passed. This
  experiment does not reclassify those unrelated failures.
