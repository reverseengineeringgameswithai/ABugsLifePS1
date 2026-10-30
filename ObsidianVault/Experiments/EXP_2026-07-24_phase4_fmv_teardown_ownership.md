---
kind: experiment
id: EXP_2026-07-24_phase4_fmv_teardown_ownership
name: Phase 4 E15 static callback-teardown ownership
date: 2026-07-24
status: reproduced
confidence: confirmed_with_bounded_residuals
source_state: original_game
system: SYS_fmv_player_streaming
artifacts: [analysis/phase4_fmv_teardown_ownership.json, analysis/phase4_fmv_callback_lifecycle.json]
---
# Phase 4 E15 static callback-teardown ownership

## Question and lane

The closure ledger selected `fmv_playback` / `E15_fmv` with binding lane
`static`: reconstruct the live callback-teardown synthetic-unwind observation,
default clear stores and readers before authorizing another replay.

The already consumed external index
`derived/Phase4/fmv-skip-v1/index.json` was verified at SHA-256
`3cb3a3e30b9ca6d048531972fd3af619b330c3e50cfb997ebb61873c76f37996`
and queried at movie frames 333, 343, 362, 416 and 417. It continued to answer
the frame/residency questions, so no capsule bytes were rescanned and no live
escalation was opened. Static reconstruction used only hash-verified pristine
`SCUS_942.88` and `FMV/FMV.BIN`.

## Guest return

`0x800709AC..0x80070A30` allocates 24 stack bytes, saves `ra` at
`0x800709B0`, restores it at `0x80070A20`, restores `sp` at `0x80070A24`, and
executes `jr ra` at `0x80070A28` with a nop delay slot. Its caller at
`0x800B74A4` has return continuation `0x800B74AC`.

The retained functionTrace event remains exactly labelled
`exit_is_synthetic_unwind: true`; it is not rewritten. The guest byte sequence
contains a conventional balanced return, so that observer label is not evidence
for a guest synthetic-return edge.

## Callback and register interfaces

The default ready API at `0x8006D8D0` swaps resident pointer slot
`0x800818C8`. The exhaustive direct census contains eight xrefs: five reads,
three writes, two initialization clears and four guarded callback dispatches at
`0x8006E5D8`, `0x8006E860`, `0x8006ECD0` and `0x8006F61C`.

The default data wrapper `0x8006DCF0..0x8006DD14` calls
`DMACallback(3, callback)`. The SDK entry dispatches through field +4 of the
kernel table loaded via `0x80080DE0`, with `jalr` at `0x8006544C`.
Kernel-private callback storage remains opaque and is not game-owned MOD state.

When mode `0x800818E8 == 1`, teardown instead calls the FMV.BIN channel-3
wrapper `0x800B9A28` and ready-slot swap `0x800B9A14` at overlay slot
`0x800CAECC`. The direct resident census proves teardown's mode read, not
runtime reachability through unknown indirect writers.

The four retained endpoint words decode little-endian to
`0x1F801800..0x1F801803`. Pristine executable bytes prove these are the
resident CD-ROM MMIO pointer table at `0x80081C28..0x80081C37`, not callback
storage. Teardown writes zero through the first and fourth cells to registers
0 and 3. Equal pointer cells across endpoints are expected and do not observe
the volatile target bytes.

## Result and residuals

`analysis/phase4_fmv_teardown_ownership.json` retains exact opcodes, both
backends, all ready-slot xrefs, the SDK boundary, pointer-table identity, both
target stores and the live/static reconciliation. Mutation tests reject a
changed guest return, missing slot xref, changed pointer cell, changed FMV
caller and changed retained live event.

This closes the E15 callback/MMIO/return teardown sub-boundary with confirmed
confidence. It does not promote subsystem-wide `original_interfaces`: remaining
level/viewer completion and transition writers plus the E12 audio, C17
movie-viewer, E14 persistence, and E16 overlay/resource-loader contracts still
intersect that dimension. Pause, repeat, decode/CD failure, malformed-stream
outcomes, and the 36 live manifest paths also remain open. No live replay,
MOD-private state, hook or intended behavior was introduced.

See [[SYS_fmv_player_streaming]],
[[EXP_2026-07-24_phase4_fmv_callback_lifecycle]], and
[[Game Solving Campaign - FMV Playback and Skip]].
