# Phase 4 FMV player-exit ownership

## Scope

This iteration retained only `fmv_playback` / `E15_fmv` and the first unmet
`lifecycle` dimension. It tested one claim: the pristine player's complete
post-helper predicate and Stop/Pause command partition can be reconstructed
from the retained derived index plus hash-verified FMV/resident code, without
another emulator replay.

The explicit falsifier was any pre-existing exact index answer, another edge
into `0x800B6E38`, `0x800B7464` or `0x800B7468`, a missing producer chain,
controller mask/count drift, completion not issuing command 8 before command
11, an inferred runtime outcome, or a load-bearing mutation that stayed green.

## Offline localization

The ordered Phase-4 regeneration selected E15 alone. The relevant retained
`fmv-lifecycle-v2` index has SHA-256
`e232f9cd3da57de3f794495b0789904c6cb36bd8152e67f3f7d12576d5c828ab`
and 16,060,589 bytes.

Closed receipt
`244e5b5ac038d6b9b805a13581007d36cfe4cd268e3f8881c8ed80d7e2b4aa0d`
re-executes `tools/phase4_offline_receipt_query.py` over the centrally
preserved copy. The bounded exact search covers the five exit PCs, mask
`0x4008`, `CdControl`, `CdlStop`, `CdlPause`, and `post-helper exit`.
Every term returns zero paths without truncation. Output SHA-256 is
`13a98c8d30b51de9b60e9d05171ab3ff12459b42b66a68167002c6a7ccfc2142`.
The missing fact was therefore instruction-level ownership, not another
frame-boundary query.

## Static reconstruction

`analysis/phase4_fmv_player_exit_ownership.json` regenerates from pristine
`FMV/FMV.BIN` and `SCUS_942.88`. It classifies five exact predicates:

- `0x800B7294`: u8 decode-stop latch value one;
- `0x800B7428`: resident CD-event field value one;
- `0x800B7430`: controller-derived countdown value twelve;
- `0x800B7444`: completion request value one;
- `0x800B745C`: decoded index remains below the signed selected limit.

The resident function `0x8003A2DC..0x8003A314` copies the previous controller
halfword, polls port one, and publishes the current halfword at `0x80082412`.
The player calls it at `0x800B70E0`, applies exact mask `0x4008`, seeds the
countdown at one, increments it per active outer iteration, and compares it
with twelve.

The complete FMV executable-code scan finds exactly six encoded entries into
the Stop/Pause/common-argument blocks and no unclassified edge. Completion
alone enters `0x800B6E38`, issues `CdlStop(8)`, and sets `CdlPause(11)` in the
join-jump delay slot. Latch, CD-event, controller sentinel, initial-limit, and
ordinary limit exhaustion reach the shared Pause/common teardown without the
Stop call. `CdlPause(11)` is libcd stream teardown, not the frontend pause
shell.

## Result and boundary

The falsifier survived. Focused guards recompute both pristine identities,
the closed offline receipt, all load/compare opcodes, the complete encoded
edge census, controller producer chain, command ordering, and non-promotion
boundary. Mutating mask `0x4008`, adding another encoded teardown edge, or
breaking the resident controller store turns the guard red.

This closes only `post_helper_exit_and_cd_command_ownership`. It does not
promote lifecycle, establish native CD-event frequency, claim malformed-stream
outcomes, generalize to every selector/viewer path, or identify the first
caller-owned Region-B overwrite. No DuckStation process launched and no live
receipt was authored.

The next lane remains static: identify the first caller-owned Region-B
overwrite after one selected level/viewer return and classify its E16/E14
owner before considering another live control.
