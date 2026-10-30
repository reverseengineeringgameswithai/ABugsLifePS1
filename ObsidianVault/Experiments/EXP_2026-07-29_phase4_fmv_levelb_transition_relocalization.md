---
campaign: fmv_playback
row: E15_fmv
dimension: lifecycle
status: static_relocalization_closed
---

# Completed-Level-B transition re-localized before frame 15816

The measured packet retained only `fmv_playback` / `E15_fmv`; the first
unmet dimension remained `lifecycle` and the binding lane was `static`.
Recursive operator and centrally provisioned movie inventories were reviewed
before selection. The existing `fmv-lifecycle-v2` derived index contains no
LEVEL01 instruction or DMA event stream, so it could not answer the remaining
instruction-boundary question.

## Offline observation

A new closed `abl-phase4-offline-query/1` receipt projects one already
retained derived-pristine exact-PC batch result without retaining captured
memory bytes in the repository. Its input SHA-256 is
`5afa281a79ce3520360127cca4a303d408b19a455d8a1cfbc391a4cff8e36625`;
its byte-identical output SHA-256 is
`bb2893a11cab61cf35aa2088353531b697fd6c01d183bfb2ef19d7f5af0767d0`.
Receipt SHA-256
`aedb9bb4905be6750f4fbde8c60bf5c0a5833e686411038bde7fde5ea4f4faa7`
pins `tools/phase4_atomic_anchor_projection.py`.

The observation is exact but narrow: frame `15816`, cycle `8954497636`, is
paused at resident scene-flow wait PC `0x8004FEA4`. The Region-B head hashes
to `6245e366...3a1b8`, not the retired FMV.BIN head
`ab33c205...54db`. This proves that the prior frame-15816 start was already
post-retirement. It does not identify a DMA event, transfer cycle, sector
sequence, or the selected earlier branch.

## Static reconstruction

Hash-verified pristine executable bytes and the centrally pinned scene-flow
ASM close the complete earlier completed-Level-B scene-setup call set:

- negative pending request: `0x8004FD74`,
  `scene_setup_and_load(3, 0)`;
- nonnegative pending request: `0x8005029C`,
  `scene_setup_and_load(6, 128)`.

The second call has exactly three incoming resident branches
(`0x8004FDF8`, `0x80050124`, `0x80050248`), each setting scene `6` in its
delay slot. Both transition values differ from the `-1` resource-skip
sentinel, so both reach selector-zero `bits\memory.bin` loading for
`0x800B5788` before the later, now-retired `0x80046078` CdRead boundary.

`analysis/phase4_fmv_levelb_transition_relocalization.json` separates the
retained observation, static confirmation, inference, and absent causal
confirmation. Mutation guards reject drift at either scene-setup boundary,
the skip sentinel, a nonnegative predecessor, or the selector-zero
destination.

## Boundary and handoff

This closes only the re-localization sub-boundary. The natural branch and its
frame/cycle, the first Region-B DMA event, and fresh campaign-verifier
acceptance of the three prior live receipts remain open. No new DuckStation
run was justified and no lifecycle or other nine-dimension claim is
promoted.

The next lane remains `static`: implement and mutation-guard a typed first-hit
boundary that accepts either `0x8004FD74` or `0x8005029C` from an earlier
anchor. Do not replay the escaped frame-15816 `0x80046078` window.

Campaign handoff: [[Game Solving Campaign - FMV Playback and Skip]].
