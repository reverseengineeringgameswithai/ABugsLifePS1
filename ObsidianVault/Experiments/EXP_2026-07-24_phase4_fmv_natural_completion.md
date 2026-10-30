# Phase 4 E15 no-input common-exit reachability control

## Question

Does the pinned no-input LEV1A branch reach the same player common-exit
interfaces as Start-skip after the retained 541-frame capsule horizon, and
does callback teardown return the same way? This receipt asks about
reachability, not what causes the converging exit.

This was the closure-debt scheduler's single selected live lane for
`fmv_playback` / `E15_fmv`. It does not ask about another manifest path,
movie-viewer policy, audio, persistence or generic overlay loading.

## Existing evidence first

The required ordered regeneration retained 55/55 capsules, a 107-row queue
with 16 complete and 91 open rows, zero `offline_ready`, 42
`offline_partial`, zero `live_required` and 65 `no_capsule`, nine derived
indexes covering 34 rows, and one selected campaign.

Before live work, the already retained 1,875,785-byte
`derived/Phase4/fmv-skip-v1/index.json` was verified at SHA-256
`3cb3a3e30b9ca6d048531972fd3af619b330c3e50cfb997ebb61873c76f37996`
and queried at E15 movie frames 333, 343, 362, 416 and 417. It answers the
Start-branch frame-boundary domains and ends at the movie/capsule horizon; it
cannot supply a no-input counterfactual beyond frame 541.

The retained 541-frame native control already proves that no-input remains
inside exact FMV.BIN at emulator frame 4776, STR backloc 162 of selected limit
386, without entering player-exit `StClearRing` or `callback_teardown`.
Static pristine reconstruction already binds the common call sites
`0x800B749C` and `0x800B74A4` and callees `0x8007094C` and `0x800709AC`.
Only longer native runtime reachability was absent. Event-aligned completion
cause was not part of this experiment.

## Escalation and execution

`P4-ITER81-E15-NATURAL-LEVELA-COMPLETION-CONTROL` predeclared the precise
missing horizon, every relevant capsule/index/static answer, the two-job
experiment and the same-anchor control. The complete preserved 207-file
2026-07-18 runtime validated against `SHA256SUMS`; the standalone archived
executable was not launched.

`config/phase4_fmv_natural_completion_batch.yaml` defines two serialized
`scenario.loadStateAndRun` jobs:

- both inspect and reload the hash-pinned E15 save;
- both verify mounted pristine CUE SHA-256 `46310218…d644`, BIN SHA-256
  `2aeafad7…4566` and serial `SCUS-94288`;
- both advance exactly 1,500 frames and use the same two-function
  `functionTrace` plus atomic capture;
- `start_skip_positive` plays the exact pinned movie whose only active input is
  Start at frames 334 through 342;
- `natural_completion_control` supplies no movie/input.

The fresh isolated profile was
`/var/tmp/abl-p4-e15-natural.xssVOl`, dedicated port 24682, owned PID 488855.
The launcher stopped that PID and removed `instance.pid`. A separate external
531-byte cleanup receipt is retained at SHA-256
`cab677355e1ab3d141bc260cda4be05d5109c2560f3e7dfd5312ef0d17c747b3`;
later validation does not depend on the transient profile directory existing.

The external result is 51,177 bytes at:

`~/Downloads/ABL-external-evidence/live/Phase4/e15-natural-levela-v1-20260724/result.json`

SHA-256:
`0f695036639692142307c5a9a212874e7677faa5d1d50e4060ec8566209c0cee`.
Raw receipt, movie, save, disc and capture bytes remain outside Git.

## Observations

Both jobs reproduce shared initialization at emulator frame 4443:

- `StClearRing` entry/exit cycles `2515397349` / `2515399779`;
- caller `0x8006D3BC`, return `0x8006D3C4`.

Start-skip reaches the player common exit at emulator frame 4671:

- `StClearRing` from `0x800B749C`, entry/exit cycles
  `2644271877` / `2644274307`;
- `callback_teardown` from `0x800B74A4`, entry/exit cycles
  `2644274321` / `2644284120`;
- the retained FunctionTrace exit remains a synthetic unwind.

No-input reaches those same call sites at emulator frame 5305:

- `StClearRing` entry/exit cycles `3003377970` / `3003380400`;
- `callback_teardown` entry/exit cycles `3003380414` / `3003384397`;
- teardown returns normally (`synthetic_unwind=false`).

The no-input common exit is 634 emulator frames later than Start-skip and 529 frames
beyond the earlier retained no-input endpoint. Both 1,500-frame endpoints no
longer have FMV.BIN identity in Region B. No Region-B typed field is
interpreted after that failed identity guard.

## Conclusion and boundary

For this inspected pristine LEV1A anchor, no-input reaches the same player
common-exit interfaces as Start-skip. This receipt alone does not distinguish
selected-limit completion from a stop, timeout, failure, or another
completion-request writer. The Start trace's
synthetic unwind is not a general guest-return property: natural teardown
returns normally, consistent with the separately reconstructed conventional
epilogue.

This closes one level-A reachability fact, not its cause. The successor
instruction-attributed experiment is
[[EXP_2026-07-24_phase4_fmv_natural_exit_cause]]. Lifecycle and original
interfaces remain partial.

## Guards

`tools/phase4_fmv_natural_completion.py --write --check` revalidates the
external result and cleanup receipts, plan, fixture/media/debugger identity,
prior 541-frame boundary, exact event callers/returns/frames/cycles and
endpoint residency guard. `tests/test_phase4_fmv_natural_completion.py`
mutates the natural caller, unwind classification, media hash, endpoint
overlay bytes, cleanup payload and run bound.
`analysis/phase4_fmv_natural_completion.json` retains only the bounded
non-copyrighted reachability summary and external hashes.

Original-game facts are promoted to [[SYS_fmv_player_streaming]]. Campaign
scope and next work remain in
[[Game Solving Campaign - FMV Playback and Skip]]. No MOD-private state, hook
or intended behavior was introduced.
