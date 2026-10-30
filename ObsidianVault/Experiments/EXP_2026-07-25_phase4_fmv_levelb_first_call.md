---
kind: experiment
id: EXP_2026-07-25_phase4_fmv_levelb_first_call
date: 2026-07-25
phase: 4
campaign: fmv_playback
row: E15_fmv
status: reproduced_bounded
confidence: high
source_state: original_game
artifact: analysis/phase4_fmv_levelb_first_call.json
---

# Natural completed-Level-B first call and lifecycle

## Question and prior evidence

The corrected passive full-level receipt proved that the centrally declared
`movies/100% Runs/LEVEL01.movie.json` naturally covers completed-Level-B caller
`0x8005031C`, while its timing-identical all-neutral derivative does not. It did
not retain the first hit, call arguments, selector/limit publication,
completion writer, or teardown.

The generated escalation
`P4-ITER89-E15-LEVELB-FIRST-CALL-LIFECYCLE` first queried the preserved
`fmv-lifecycle-v2` index. That 4,549-record index covers only the E15 skip and
C16 LOSE recordings, so it cannot answer a full-level question. Static
reconstruction already fixed the candidate chain: `0x8005031C`, the level-B
selector table, selector 11 / `BUGSFMV1/LEV1B.STR` / limit 485, all completion
writers, and the common player exit.

## Method

The run used the complete preserved 2026-07-18 runtime, not its standalone
archived executable, in fresh profile
`/var/tmp/abl-p4-e15-levelb-first-call.iter1b.24738` on loopback port 24738.
Capabilities identified API 2.1.0/schema 2026-07-18, running-binary SHA-256
`55d58903…75a8`, source revision `fe0cca16…b8f5`, and the expected dirty-state
hash. Mounted media was pristine SCUS-94288 with the centrally pinned CUE and
BIN hashes.

Twelve `movie.traceToFrame` queries binary-searched the first cumulative exact-
PC coverage target. Each query included its own uninstrumented/passive cached-
interpreter comparison. After resetting to the last absent target, exact
breakpoints and bounded execution/function/access observers captured the
caller, loader entry, limit/completion fields, stop latch and common exit for
1,800 frames. The same window and observer set were then run against an
all-neutral derivative. Both derivatives existed only in a temporary
`/var/tmp` directory and were removed before collector exit.

`scenario.runBatch` was not used for the live window because it cannot stage a
cycle-neutral recorded-anchor prelude followed by exact instruction observers
in one job. The client-driven fallback and its control were predeclared.

## Observation

- Movie frame 14,381 is the last absent target; 14,382 is the first present
  target. All 12 comparisons report same RAM, registers, cycle and frame, with
  untruncated coverage.
- At emulator frame 14,382/cycle 8,142,856,967, PC `0x8005031C` has pre-delay
  `a0=0`, `a1=0`, progress ID `s0=1`, `ra=0x800502D8`, and
  `sp=0x801FFFB8`.
- At cycle 8,142,856,981, exact loader entry `0x8003E7C0` sees `a0=11`,
  `a1=-1`, `ra=0x80050324`. The load and JAL delay slots explain the
  pre/post-delay distinction.
- `0x800B6DC0` publishes selected limit 485 at frame 14,719.
- `0x800B6B24`, the frame-order-regression writer, publishes completion
  request 0 to 1 at frame 15,763. No completion-one event from
  `0x800B6B48` and no FMV-owned decoded stop-latch write is observed.
- `StClearRing` from `0x800B749C` and callback teardown from `0x800B74A4`
  occur in order at frame 15,816. The teardown entry is not synthetic unwind.
- The all-neutral branch records no completed-Level-B caller, no loader entry
  from that caller, and no limit-485 publication. It does record generic loader
  entries from `0x8004FB68` at frame 14,385 and `0x8004FB74` at frame 16,018.

All positive/neutral execution, function, and four access traces are
untruncated. All 30 debugger cleanup actions succeeded. The external result is
779,928 bytes, SHA-256 `d7996d79…ae4d`; its 490-byte cleanup receipt is
`9a17e886…f28e`, records owned PID 52516 stopped, and confirms that no
credential was retained in the result.

## Rejected hypotheses

The natural selector-11 stream does not complete through the LEV1A
selected-limit writer `0x800B6B48`; it uses `0x800B6B24` on this run. The
all-neutral branch is also not globally free of FMV loader calls. Its divergent
frontend route uses the loader twice, so the negative control is correctly
scoped to the completed-Level-B caller, caller-owned loader entry, and limit
485.

Earlier diagnostic profiles were stopped by their owning launcher and retained
no result because they respectively exposed pre-delay register semantics,
insufficient completion capacity, the alternate completion writer, exact
post-delay loader arguments, or the over-broad neutral-loader assertion.

## Banking and boundary

`config/phase4_fmv_levelb_first_call.yaml` pins the fixture, media, debugger,
profile, external receipts and expected low-level events.
`tools/phase4_fmv_levelb_first_call.py` regenerates the tracked summary directly
from those events; mutation tests reject neutrality, call/register, writer,
teardown, truncation, control and cleanup drift. Original-game facts are
promoted to [[SYS_fmv_player_streaming]]. No MOD-private state, hook, or
intended behavior was introduced.

This closes the exact first-call/selector/limit/completion/teardown sub-boundary
for one natural Level-B stream. It does not close other Level-B IDs,
alternate/advert/viewer playback, pause/repeat, decode/CD failures, campaign
breadth, lifecycle, cross-system interfaces, or E15 as a whole. No roadmap
dimension is promoted.
