# Phase 4 E15 selected-limit completion cause

## Question

Which exact writer causes the pinned pristine LEV1A no-input path to select
the common exit at emulator frame 5305? The earlier 1,500-frame receipt proved
only reachability because it retained endpoint memory after FMV.BIN retirement.

## Offline and static narrowing

The ordered regeneration validated 55/55 retained capsules, a 107-row queue
with 16 complete and 91 open rows (`offline_ready=0`,
`offline_partial=42`, `live_required=0`, `no_capsule=65`), nine preserved
derived indexes covering 34 rows, and only `fmv_playback` / `E15_fmv`
selected with binding lane `live`.

The existing external `fmv-skip-v1` index was reused at SHA-256
`3cb3a3e30b9ca6d048531972fd3af619b330c3e50cfb997ebb61873c76f37996`.
Its 542 E15 frame-boundary rows cover Start and end at the movie horizon; they
cannot observe the no-input event at emulator frame 5253. Static pristine
reconstruction limits the discriminators to completion writers `0x800B6B24`
and `0x800B6B48`, stream-start clear `0x800B6DD0`, selected-limit writer
`0x800B6DC0`, late backloc writer `0x80070A8C`, and decoded-record stop writer
`0x800B6C84`.

Escalation `P4-ITER82-E15-NATURAL-EXIT-CAUSE-CONTROL` therefore requested only
instruction-attributed access provenance around the already reproduced
boundary.

## Atomic control

`config/phase4_fmv_natural_exit_cause_batch.yaml` uses two serialized
`scenario.loadStateAndRun` jobs from the same inspected save, pristine
SCUS-94288 media, 1,100-frame bound, four access watches, two-function trace
and atomic capture. The sole input difference is the exact Start-only movie
in the positive job.

The complete preserved 207-file 2026-07-18 runtime was launched from its
app-root. The fresh profile
`/var/tmp/abl-p4-e15-natural-cause.1TRfUS` used port 24683 and owned PID
650015. The launcher stopped that PID; a separate 537-byte cleanup receipt at
SHA-256
`ef3c4d61fa0f3109820857db2a4181276daec587484c5f78814a0528ac6dd856`
proves `instance.pid` absent, the PID dead, and no credentials retained.

The 80,569-byte external batch result remains outside Git at SHA-256
`9eb4310e9f026809ae2a0b64e0412cd0768d1ee310b1944ae0fb9c562d77c689`.

## Observation

On the no-input branch, with exact FMV.BIN still resident:

- `0x800B6DC0` writes selected limit 386 at frame 4418;
- `0x800B6DD0` clears completion request at the same stream start;
- `0x80070A8C` advances late backloc `378→381`, `381→384`,
  `384→385`, then `385→2` at frames 5210, 5216, 5219 and 5233;
- `0x800B6B48` writes completion request `0→1` at frame 5253,
  cycle 2973774887;
- the decoded-record stop-latch watch records zero writes;
- balanced `StClearRing` / `callback_teardown` follows at frame 5305.

The completion write occurs after the run has reached backloc 384 of selected
limit 386. It is not simultaneous with that backloc sample. The access ring is
untruncated. The Start control reaches its known frame-4671 exit, but watched
addresses after its FMV.BIN retirement are deliberately untyped and are not
used as causal evidence.

## Conclusion and boundary

For this one pristine LEV1A no-input run, selected-limit writer `0x800B6B48`
causes completion before the common exit, with no resident decoded-record
stop-latch write. This distinguishes the frame-order writer, stream-start
clear and decoded-record stop path for this run.

It does not promote lifecycle: level-B, alternate, lose, advert and viewer
breadth; pause/explicit stop/repeat; unload/reload; timeout, CD and malformed
stream failures remain open. E12/C17/E14/E16 retain their adjacent interfaces.

## Guards

`tools/phase4_fmv_natural_exit_cause.py --write --check` rebuilds
`analysis/phase4_fmv_natural_exit_cause.json` from the hash-pinned result and
cleanup receipts. It verifies plan, debugger, state, pristine media, exact
events, ordering, resident endpoint and common-exit sequence.
`tests/test_phase4_fmv_natural_exit_cause.py` falsifies writer PC, stop-latch,
trace truncation, endpoint, plan and cleanup assumptions. No copyrighted or
operator-owned bytes are committed.

Original-game facts are promoted to [[SYS_fmv_player_streaming]]. Campaign
scope remains in [[Game Solving Campaign - FMV Playback and Skip]]. No
MOD-private state or hook was introduced.
