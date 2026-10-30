---
campaign: fmv_playback
row: E15_fmv
dimension: lifecycle
status: pre15792_request_acceptance_return_boundary_closed
---

# Completed-Level-B pre-15792 predecessor and state partition

The measured packet retained only `fmv_playback` / `E15_fmv`; lifecycle was
the first unmet dimension and `static` was the binding lane. Recursive
inventory found 110 files under the operator Phase-4 movie tree, 147 under
the broader operator movie tree, 135 centrally provisioned files and 100
centrally provisioned Phase-4 files. No operator fixture was imported.

Ordered regeneration reproduced 55/55 capsules and 3,391,058,326 preserved
external bytes; the 107-row opportunity queue remained 91 open, 42
offline-partial and zero offline-ready; the derived index retained nine
indexes over 34 rows; and the closure-debt scheduler selected only E15 at
four of nine dimensions.

## Offline localization

The existing `fmv-lifecycle-v2` index was queried first with the tracked
`tools/phase4_offline_receipt_query.py`. Receipt SHA-256
`c473416e539fe1e5bc30b5af47ec5e0f341be77275e2986a62ff46c28b9fc169`
pins input
`e232f9cd3da57de3f794495b0789904c6cb36bd8152e67f3f7d12576d5c828ab`
and output
`e37835b3823f8eb63cbc30994b8146eccf736582cbaf01c9644a8761e5bd7f1e`.
It contains no exact E15 candidate PC, completed-Level-B, Region-B, or late
frame lead; 708 retained `0x8004FEA4` values belong to other covered
capsules. The retained index cannot identify the natural LEVEL01 first hit,
so no capsule bytes were rescanned.

A second bounded reader projected the already retained current-toolchain
passive batch without copying memory payload into Git. Receipt SHA-256
`1a50ea873c8a4c0ff682ee9445af95cf93c03b27d66af9e0b86fef11dc37de87`
pins batch
`ee8b36d851409dfa4dcdc8c6ab3fd1c7912c874d49f18b19e4c76466912cf414`
and output
`f95160f056245147d13802a03d30f195e4efe3bb7bb46c5d73e26a5f401c513a`.
Both pristine cold-boot jobs are at emulator frame 15720, cycle 8900142073,
PC `0x8004FEA4`, SP `0x801FFFD0`. This falsifies the tempting interpretation
that frame 15720 is still inside the FMV overlay. It is a resident
wait-control position, not a candidate hit or Region-B memory observation.

## Static reconstruction

The pristine scene-flow function has three direct
`scene_setup_and_load` calls. `0x800500E4` is the non-intersecting natural
LOSE continuation. The completed-Level-B candidate set remains exactly:

- `0x8004FD74`, `(scene, transition) = (3, 0)`, with one negative
  `pending_scene_request` predecessor;
- `0x8005029C`, `(6, 128)`, with one early nonzero
  request-acceptance-return predecessor at `0x8004FDF8` and two nonnegative
  `pending_scene_request` predecessors at `0x80050124` and `0x80050248`.

The changed static decomposition closes the formerly opaque early edge.
`0x8005B4E4..0x8005B70C` initializes the returned `s5` bit to zero at
`0x8005B4F4` and has exactly one setting instruction, `0x8005B63C`. That
setter is reachable only after decoded-input bit 0 at `0x80082412` is
present, the local `s0` one-shot gate is clear, and a fresh s32 load from
`0x8009EDCC` is nonnegative. The bit is copied at `0x8005B6C8`, saved by
the wrapper at `0x8005B850`, never redefined before wrapper return copy
`0x8005BC40`, then consumed by branch `0x8004FDF8`.

This corrects the broad shorthand that all three predecessors of
`0x8005029C` are direct pending-request tests: the early edge consumes a
derived pending-request acceptance bit. The s32 resident
`pending_scene_request` field is at `0x8009EDCC`. A complete
compiler-standard adjacent-LUI/direct-LW-or-SW census classifies thirteen
direct xrefs: ten reads and three stores, with zero unclassified direct
xrefs. Non-adjacent pointer aliases remain an explicit residual.

The wait loop stores and compares value one through resident u32
`0x80082250`. Relative to that static control position, the negative-request
and request-acceptance-return predecessor classes are before the wait; the two later
pending-request classes are after it. This partitions code positions only.
It does not prove whether a before-wait candidate already retired or a later
candidate will execute.

Generated artifact
`analysis/phase4_fmv_levelb_pre15792_partition.json` joins both closed
offline receipts, the falsified `15792..15856` live window, pristine
function/opcode identities, all four predecessors, the transitive return
def-use contract, the typed state census, selector-zero `bits\memory.bin`
replacement, and mutation guards.

## Boundary and handoff

No DuckStation process launched, no live escalation was added, and no
natural branch, exact retirement frame, DMA event or roadmap dimension is
promoted. The first-hit event still lacks instruction-granularity evidence
before frame 15792; the frame-15720 status and the transitive static
predicates cannot safely choose a new live window.

This iteration changed the static decomposition and closed a genuinely new
return/interface boundary. The next iteration must choose a different static
lifecycle question or scheduler lane instead of replaying the escaped
two-PC observer under another label. The controller reliability repair that
pins verifier decisions to integer phase 4 is trial infrastructure only and
receives no Phase-4 evidence credit.

Original-game facts: [[SYS_fmv_player_streaming]]. Campaign handoff:
[[Game Solving Campaign - FMV Playback and Skip]].
