---
kind: experiment
id: EXP_2026-07-24_phase4_fmv_callback_lifecycle
name: Phase 4 E15 same-anchor callback lifecycle control
date: 2026-07-24
status: reproduced_partial
confidence: confirmed_with_bounded_residuals
source_state: original_game
system: SYS_fmv_player_streaming
artifacts: [analysis/phase4_fmv_callback_lifecycle.json, analysis/phase4_live_escalations.json]
---
# Phase 4 E15 same-anchor callback lifecycle control

## Question and authority

Does the existing Start-only E15 movie cause the statically reconstructed
player common exit to call `StClearRing` and callback teardown, while the same
inspected save advanced without input avoids those interfaces?

The centrally pinned capsule/index first localized the Start frames, passive
frame-362 blocks, and FMV.BIN residency boundary. Pristine static bytes then
bound player call sites `0x800B749C` and `0x800B74A4` to functions
`0x8007094C` and `0x800709AC`. Neither source supplies runtime call order or a
no-input counterfactual, so the closure ledger authorized one atomic live
control under escalation
`P4-ITER79-E15-CALLBACK-TEARDOWN-CONTROL`.

The existing central fixtures and pristine media were verified as:

- movie SHA-256
  `ca5219db048a986605bb20c2376166e9014645c7da87c8347a6e6ec0fb681fba`;
- state SHA-256
  `851e8ebffa8b8417abb30ff0791ca4c1872a43cf06101247ee1ff97e4cdac417`;
- mounted CUE/BIN SHA-256
  `463102187c2ada6ac90c2990e23cdaf2ef9f8eb56a95a57d8ab496248571d644` /
  `2aeafad70d12b1bd0dc63bbb106f22ced4fae070cea8eef9de4f11072e944566`;
- serial `SCUS-94288`.

The complete preserved 2026-07-18 runtime was launched, not its archived
standalone executable. Its running executable SHA-256 was
`55d589032641ad0904526742f2209c034a710a162ebba3e1bc04b4c5da6075a8`;
the debugger API/schema were `2.1.0` / `2026-07-18`.

## Method

`config/phase4_fmv_callback_lifecycle_batch.yaml` defines two serialized
`loadStateAndRun` jobs. Both retain the verified mounted disc, inspect and load
the same state, arm a 16-event trace for only `0x8007094C` and `0x800709AC`,
advance the same frame count, and take the same atomic register/memory/trace
capture. The positive starts the exact pinned movie; the negative supplies no
movie. The only intended variable is its nine Start samples at movie frames
334..342.

Three fresh `/var/tmp` profiles were used as the hypothesis narrowed. Owned
PIDs 47649, 49318 and 53966 were each stopped after debugger instrumentation,
movie and controller cleanup. Raw receipts remain external and are preserved
by exact hash in `analysis/phase4_fmv_callback_lifecycle.json`.

## Observations and falsifications

The first 363-frame batch falsified the predeclared frame-362 hypothesis. Both
controls recorded only one shared balanced `StClearRing` call from
`0x8006D3BC` at emulator frame 4443; neither recorded callback teardown.
Passive frame-block starts were therefore not call evidence. Receipt SHA-256:
`09288541e2c9e5067335902439f5d5ffb7eca005eb50c8721f09a3d38cdac842`.

The 418-frame batch targeted the capsule's passive 416-to-417 retirement
boundary. It again recorded only shared initialization, and the positive still
retained exact FMV.BIN at emulator frame 4653. Function tracing changed the
live schedule relative to the passive capsule, so that capsule boundary was
rejected as an exact live trigger. Receipt SHA-256:
`f984c57715539b17b3031cbb17a10ac1a562f02bb724c646d5e2a52d77d4d88f`.

The final bound used the already pinned 541-frame movie endpoint. Both controls
again reproduced shared initialization:

- `StClearRing` entry/exit at cycles 2515397349/2515399779;
- caller/return `0x8006D3BC` / `0x8006D3C4`;
- emulator frame 4443.

Only Start-positive then executed the player common exit at emulator frame
4671:

- `StClearRing` from `0x800B749C`, return `0x800B74A4`, entry/exit cycles
  2644271877/2644274307;
- callback teardown `0x800709AC` from `0x800B74A4`, return `0x800B74AC`,
  entry cycle 2644274321;
- its functionTrace event at cycle 2644284120 is labelled a synthetic unwind
  with `v0=1`. This is an observer-stack classification; the follow-up static
  reconstruction proves the guest function itself has a conventional balanced
  epilogue and caller continuation.

At the endpoint the positive no longer had exact FMV.BIN at Region B. The
no-input control recorded neither player-exit call and retained the exact
FMV.BIN head. This proves Start-only sufficiency for this interface sequence at
the inspected anchor. Final receipt SHA-256:
`4e752c98d2a780a1047c77dd33b68a3dfb2c696b504f755c0303a2fd3b59b5b8`.

The four captured words at `0x80081C28` are
`0018801f0118801f0218801f0318801f` in both endpoint captures. Therefore the
earlier hypothesis that callback teardown clears those captured *cells* before
the endpoint is false. Follow-up pristine-byte reconstruction identifies them
as the immutable pointer table `0x1F801800..0x1F801803`; teardown writes through
the first and fourth cells to MMIO register targets. Equal pointer cells do not
test those target bytes. Static callback clears, target writes and the retained
functionTrace label remain distinct facts.

## Result and residuals

The live result closes one named callback-interface fact but does not promote
the E15 lifecycle dimension. The subsequent static campaign
[[EXP_2026-07-24_phase4_fmv_teardown_ownership]] closes the guest-return,
callback-slot and pointer-target ownership questions without rewriting this
receipt. Pause, explicit stop, repeat, alternate caller, decode/CD failure and
malformed-stream paths remain open.

The tracked generator recomputes all three external hashes, debugger/media/state
identity, batch completion, exact event caller/order/frame/cycles, endpoint
residency and cleanup receipts. Mutation tests fail on changed caller, false
negative teardown, media drift, residency drift or plan-bound drift. No movie,
save, disc, capture or raw debugger receipt is committed.

See [[SYS_fmv_player_streaming]] and
[[Game Solving Campaign - FMV Playback and Skip]]. No MOD-private state, hook
or intended behavior was introduced.
