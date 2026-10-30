# Phase 4 E15 natural game-over LOSE lifecycle

## Question

Can a distinct pristine game-over path bind the natural LOSE selector, stream
limit, completion writer and balanced player teardown without repeating the
already reproduced LEV1A anchor?

## Offline and static narrowing

The required ordered regeneration validated 55/55 retained capsules
(3,391,058,326 external bytes), a 107-row queue with 16 complete and 91 open
rows (`offline_ready=0`, `offline_partial=42`, `live_required=0`,
`no_capsule=65`), nine preserved derived indexes covering 34 rows, and only
`fmv_playback` / `E15_fmv` selected with binding lane `live`.

The movie inventory supplied the lead
`movies/Phase4/C16_gameover_continue.movie.json`; its C16 capsule, save and
pristine media were independently hash-verified before interpreting it.
Offline frame reconstruction localizes a selector/load window after directional
input, selected limit `0→281`, completion `0→1`, and later frontend reuse.
Static pristine reconstruction identifies the direct
`0x800500D8 -> 0x8003E7C0` loader call, selector 46 / mode 0,
`BUGSFMV2/LOSE.STR`, limit 281, player common-exit call
`0x800B749C -> 0x8007094C`, and callback teardown
`0x800B74A4 -> 0x800709AC`.

Escalation `P4-ITER83-E15-LOSE-GAMEOVER-LIFECYCLE-CONTROL` requested only the
missing instruction-resolution loader, completion and interface ordering.

## Preferred atomic attempt and method change

`config/phase4_fmv_lose_lifecycle_batch.yaml` first ran a two-job atomic
positive/no-input control through `tools/phase4_duckstation_batch.py`. The
movie-positive reached playback index 1600 but reported
`movie_reproducible=false`, produced zero precise loader/limit/completion
events, and byte-matched the no-input scene-9 endpoint. That result is retained
as failed observer-desynchronization provenance, not behavioral evidence.

The escalation ledger was updated before continuing. The bounded fallback
`tools/phase4_fmv_lose_staged_live.py` consumed the directional input through
DuckStation's internally controlled cached replay to movie frame 300, verified
a cycle-neutral internal control plus RAM/VRAM/SPU fingerprints, then armed
exact stops and access provenance only for the narrowed window. This is the
required experiment-design change after the earlier LEV1A iterations.

## Observation

The reproducible staged positive records:

- cached movie frame 300 at emulator frame 265511, PC `0x8004FEA4`, with RAM,
  VRAM and SPU-RAM hashes matching its internal control;
- `fmv_bin_load` entry at frame 265655 / cycle 150414500700 from
  `0x800500D8`, selector 46, mode 0, return address `0x800500E0`;
- selected-limit writer `0x800B6DC0` writing 281 at frame 265826;
- stream-start clear `0x800B6DD0` writing completion `0→0` at the same frame;
- completion writer `0x800B6B48` publishing `0→1` at frame 266492;
- shared initialization `StClearRing` from `0x8006D3BC`, then player common
  exit `0x800B749C -> 0x8007094C` and callback teardown
  `0x800B74A4 -> 0x800709AC` at frame 266545; and
- loader return to `0x800500E0` at movie frame 1337 / emulator frame 266548,
  with scene 9, latch 0, completion 1, selected limit 281 and the exact
  FMV.BIN head still resident.

The access ring is untruncated and the staged movie remains reproducible. The
same-save no-input atomic job reaches no loader, selected-limit or completion
event; because the failed frame-zero observer invalidated its positive, that
job is only a negative interface control, not the counterfactual paired with
the staged positive.

## Preservation and cleanup

The raw movie, save, disc and debugger receipts remain external. The 69,996-byte
failed atomic result is pinned at SHA-256
`e0d5d0d3476bb20b5a18f59c41efe243e307faa458e2a7e703c8686aafed42c1`;
the 166,754-byte staged result is pinned at
`392d1055a8942cb26b43d89e703b0bf171af8340d9c193623fd3bdf627b712a0`.
Their cleanup receipts are
`d2bbb8ebc2be15565d8d27889572455776f809378997dc2f711a0fc12205b4be`
and
`168404d59b055516dfb60dd4b4e12c66ba20fe0946728c4303157012d73709c4`.
Fresh profiles used dedicated ports 24684 and 24685; owned PIDs 924215 and
932871 were stopped.

## Conclusion and boundary

This binds one distinct natural game-over LOSE selector/load/completion and
balanced common-teardown path. It reduces a lifecycle and original-interface
residual but does not promote a dimension. Alternate continue/quit choices,
level-B, alternate, advert and viewer paths, pause/repeat, audio presentation,
decode/CD failure and malformed-stream behavior remain open. E12/C17/E14/E16
retain their adjacent policy.

## Guards

`tools/phase4_fmv_lose_lifecycle.py --write --check` rebuilds
`analysis/phase4_fmv_lose_lifecycle.json` from the four hash-pinned external
receipts and verifies fixtures, pristine media, debugger identity, cached
control neutrality, exact stops, access writers, endpoint and cleanup.
`tests/test_phase4_fmv_lose_lifecycle.py` falsifies selector, completion writer,
trace truncation, cached-control and receipt assumptions.

Original-game facts are promoted to [[SYS_fmv_player_streaming]]. Campaign
scope remains in [[Game Solving Campaign - FMV Playback and Skip]]. No
MOD-private state or hook was introduced.
