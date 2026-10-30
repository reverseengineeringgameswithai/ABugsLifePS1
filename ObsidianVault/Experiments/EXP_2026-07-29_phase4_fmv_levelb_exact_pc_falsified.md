---
campaign: fmv_playback
row: E15_fmv
dimension: lifecycle
escalation: P4-R6-ITER4-E15-LEVELB-REGIONB-EXACT-PC-DMA-PROVENANCE
status: exact_pc_hypothesis_falsified
---

# Completed-Level-B exact-PC DMA hypothesis falsified

The measured packet retained only `fmv_playback` / `E15_fmv`. The first
unmet dimension remained `lifecycle`, and the exact claim was that the
pristine LEVEL01 cold boot would reach pre-instruction PC `0x80046078`
from a paused emulator-frame-15816 anchor before the finite frame-15880
ceiling.

The retained derived-pristine index had already answered the available
frame-boundary question: it contains no natural LEVEL01 instruction or DMA
event stream. Static reconstruction had narrowed the candidate to one
18-sector `CdRead` request to `0x800B5788`. Escalation
`P4-R6-ITER4-E15-LEVELB-REGIONB-EXACT-PC-DMA-PROVENANCE` therefore authorized
only the missing exact instruction/DMA observation and its controls.

## Observation

The passive pristine cold-boot receipt closed first over emulator frames
`15800..15896`. Two later precise runs used distinct isolated profiles,
ports, server-session IDs and owned PIDs. Both completed their paused
`scenario.runBatch` anchors at frame 15816. Both then escaped the finite
frame-15880 bound at frame 15881 before the requested `0x80046078` stop.
Each retained its last `debugger.pause` result, empty complete pagination,
normalized identity results and confirmed owned-PID cleanup.

The two precise receipt SHA-256 values are
`daa3a25d3644e81c8f77b3062bf0f566dcf1929511b170a025deeba20ae62a52`
and
`8aa9bedd679458e18fd3cebebb9328269c653b4fdcfba9da3123b0de7a57f17b`.
Their strictly wider passive-prelude receipt is
`e2303d114e7c1e5ed37093eb313bfb081ae85a3d386bc5d3a06dbe49c46893fe`.
The external receipt bytes remain under the ratchet run root and are not
committed.

## Result and boundary

`analysis/phase4_fmv_levelb_region_b_dma_exact_pc_result.json` banks the
repeated falsifier. It claims no hit at either planned PC, no DMA event and
no lifecycle promotion. Investigator receipts still require consumption by
a fresh campaign verifier; this executor note is not verification.

The current exact-PC window is retired. The next lane is `static`: re-localize
the completed-Level-B transition relative to the retained frame-15816 anchor
and reconstruct an earlier instruction boundary before another replay. This
is runtime experiment evidence, not a new original-game fact, so no Canon or
Mods claim changes.

Campaign handoff: [[Game Solving Campaign - FMV Playback and Skip]].
