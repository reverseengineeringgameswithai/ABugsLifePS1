---
kind: experiment
id: EXP_2026-07-19_phase4_offline_fmv_batch
name: Phase 4 E15 retained-capsule offline batch
date: 2026-07-19
status: reproduced_partial
confidence: confirmed_frame_boundaries
source_state: original_game
system: SYS_fmv_player_streaming
artifacts: [analysis/phase4_offline_fmv_batch.json]
---

# Phase 4 E15 retained-capsule offline batch

## Selection and authority

Iteration 72 re-read and hash-verified the acceptance contract and persistent
context, recursively inventoried all 110 Phase-4 and 147 broader movie-tree
files, and revalidated the retained capsule/toolchain surface before selecting
work. The generated queue contained 107 unique rows: 16 complete, 91 open,
zero `offline_ready`, 42 `offline_partial`, zero `live_required`, and 65
`no_capsule`. E15 was rank 5 and the highest-ranked unconsumed partial row.
C16/C15 have already been repeatedly deepened, E08 was consumed in iteration
71, and E10 already consumed its complete 13-capsule cluster.

The existing `movies/Phase4/E15_fmv_skip.movie.json` was used; no fixture was
requested or duplicated. The movie SHA-256 is
`ca5219db048a986605bb20c2376166e9014645c7da87c8347a6e6ec0fb681fba`
and its declared save SHA-256 is
`851e8ebffa8b8417abb30ff0791ca4c1872a43cf06101247ee1ff97e4cdac417`.
The retained capsule manifest/tree SHA-256 values are
`c5b3948d95f240ea3825ba15c39efb363906d3b33f41e1bf4e0b6600a85e95c6`
and `314ddbe1723317bfb430dff56af2199bf835508784f3e6f2f598dee6d574f3c3`.
Its collection control matches. The movie filename and serial remain metadata,
not mounted-media authority; pristine media/save verification and byte-identical
control are inherited from the validated central capsule manifest.

The preservation check accepted all 55/55 capsules and 3,391,058,326 external
bytes. The exact offline reader is
`~/Downloads/ABL-external-evidence/duckstation-tools/trace_capsule_query-v1-20260718.py`,
SHA-256
`b3898f928800efad5a949d1369aa65d786067505e0ed915eec8fdb99f0aa1dde`.
No DuckStation process was started.

## Exact offline batch

The nine commands emitted by the selected queue row were run unchanged:

```text
python3 ~/Downloads/ABL-external-evidence/duckstation-tools/trace_capsule_query-v1-20260718.py ~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v2/E15_fmv_skip summary
python3 ~/Downloads/ABL-external-evidence/duckstation-tools/trace_capsule_query-v1-20260718.py ~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v2/E15_fmv_skip hotspots --start 0 --end 541 --top 40
python3 ~/Downloads/ABL-external-evidence/duckstation-tools/trace_capsule_query-v1-20260718.py ~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v2/E15_fmv_skip changes --domain ram --offset 0xa6500 --length 0xb0
python3 ~/Downloads/ABL-external-evidence/duckstation-tools/trace_capsule_query-v1-20260718.py ~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v2/E15_fmv_skip changes --domain ram --offset 0x9fd80 --length 0x2100
python3 ~/Downloads/ABL-external-evidence/duckstation-tools/trace_capsule_query-v1-20260718.py ~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v2/E15_fmv_skip changes --domain ram --offset 0xb0d18 --length 0xe00
python3 ~/Downloads/ABL-external-evidence/duckstation-tools/trace_capsule_query-v1-20260718.py ~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v2/E15_fmv_skip changes --domain vram --offset 0x0 --length 0x100000
python3 ~/Downloads/ABL-external-evidence/duckstation-tools/trace_capsule_query-v1-20260718.py ~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v2/E15_fmv_skip changes --domain spu --offset 0x0 --length 0x80000
python3 ~/Downloads/ABL-external-evidence/duckstation-tools/trace_capsule_query-v1-20260718.py ~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v2/E15_fmv_skip changes --domain ram --offset 0x814bc --length 0x4
python3 ~/Downloads/ABL-external-evidence/duckstation-tools/trace_capsule_query-v1-20260718.py ~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v2/E15_fmv_skip changes --domain ram --offset 0x81530 --length 0x4
```

`tools/phase4_offline_fmv_batch.py` then used the same pinned reader once to
reconstruct all 542 records and build the repeatable external index
`derived/Phase4/fmv-skip-v1/index.json`: 1,875,785 bytes, SHA-256
`caa4bef3e219787f2178c0e8826dd6992d62af3491f780d16fcff6d9a9eb12d7`.
The index remains external game-derived evidence. Git retains only its
generator, schema, hash/size manifest, bounded findings, and mutation tests.

## Observations

- Within this retained window, the exact 0x100-byte pristine FMV.BIN head first
  appears at movie frame 69 and remains exact through frame 416. It is absent
  at frame 417; a second head-hash change occurs at frame 418.
- At frame 69, the exact head coexists with completion word `721840489` and
  selected-limit word `1`. Completion becomes 0 at frame 86, the selected
  limit becomes 0 at 168, and the LEV1A limit becomes 386 at 183.
- Stream backloc changes from 49 to 1 at frame 218, advances to 73 by frame
  362, and stays 73 through frame 541.
- The capsule independently reconstructs PC `0x80070D00` at frame 333 and PC
  `0x80065340` at frame 343. At 416 the exact overlay head is still resident;
  at 417 it is absent and Region-B completion/limit values become untyped.
- SPU-RAM has post-initial delta intersections only at frames 1..9 and
  229..362 (143 frame boundaries). VRAM changes on 118 post-initial boundaries.
  The actor pool, contact pool, and both boot-buffer words have no post-initial
  scheduled-range intersection. The player block intersects on all 541
  post-initial boundaries.
- Pretrigger/input block starts are led by FMV addresses including
  `0x800B681C`, `0x800B986C`, `0x800B9900`, `0x80070C9C`, and `0x800B6AA0`.
  The immediate response window includes `0x80065340`; this is passive
  block-start aggregation, not instruction ordering.

Observation: head identity, field resets, limit selection, backloc movement,
domain deltas, and block starts occur at the named retained frame boundaries.
Inference: the 0x100-byte identity guard establishes Region-B identity but not
that all FMV state is initialized at the first matching boundary. The existing
Start-removed live control remains the causal authority for native skip; this
offline pass neither creates nor replaces a counterfactual.

## Bounded result and remaining work

The offline batch narrows initial load/selection and overlay retirement without
an emulator replay. It does not identify the exact write/store cycle, transition
owner, DMA/GPU producer, SPU voice/event, or behavior of another manifest path.
The full 40-entry dispatch still has 36 paths without live behavioral evidence;
movie-viewer ownership, pause/stop/reuse, scene unload/reload, and failure policy
remain open. E15 stays `offline_partial` and the Audio/cinematics family stays
active at 0/2 complete.

No live escalation was authorized: no missing capsule/domain or load-bearing
native control displaced a higher-value offline batch. The generated ledger
still has six historical executed entries and zero planned entries. The queue
remains 16/107 complete with the same classification counts after registering
this consumer.

Original-game facts are promoted in [[SYS_fmv_player_streaming]]. The campaign
boundary is [[Game Solving Campaign - FMV Playback and Skip]]. Capsule
preservation is [[EXP_2026-07-18_phase4_trace_capsules]]. No MOD-private state,
hook, or intended behavior was introduced.

## 2026-07-24 current-contract supersession

The fresh iteration-84 campaign verifier found that this experiment's retained
generator no longer matched its current queue dependency. The C16 natural-LOSE
evidence had joined `movies/Phase4/C16_gameover_continue.movie.json` to E15,
making the live queue two capsules and 18 queries, but the generator still
failed closed unless it saw only the original E15 capsule and nine queries.
That failure invalidated the durable-evidence promotion while leaving the
historical 542-record findings above intact.

Iteration 85 queried `analysis/phase4_derived_index.json` first. Its exact
external source covered only the original E15 movie, so the missing C16 frame
domain was rebuilt with the same pinned reader. The current generator now
requires both capsule identities, exactly nine queries per movie, 4,007 C16
records and 542 E15 records. It preserves the result outside Git as
`derived/Phase4/fmv-lifecycle-v2/index.json`, 16,060,589 bytes, SHA-256
`e232f9cd3da57de3f794495b0789904c6cb36bd8152e67f3f7d12576d5c828ab`.
The historical `fmv-skip-v1` bytes remain untouched for old receipts.

This supersession repairs evidence breadth only. It adds no new causal or
every-cycle claim and does not promote lifecycle, interfaces, breadth,
cross-system behavior or source closure. The current campaign contract and
mutation guards are in [[Game Solving Campaign - FMV Playback and Skip]].
