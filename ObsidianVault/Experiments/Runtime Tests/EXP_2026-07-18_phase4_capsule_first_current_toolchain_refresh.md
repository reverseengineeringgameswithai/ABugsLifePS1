# Phase 4 capsule-first current-toolchain refresh

Date: 2026-07-18
Campaign state: Phase-4 freshness ratchet complete; campaign coverage remains open
Authority: hash-verified pristine retail media only; ALLMODS was not used as original-game authority

## Scope and immutable inputs

Implementation iteration 1 re-read the full acceptance contract, persistent
context, roadmap hub, linked Phase 4 execution note, feedback and trace-capsule
Experiment before selecting work. The contract SHA-256 was
`0ec2db96698c41d94fbbd2405972fe3aec63844e9b178b40abafeb4d39190700`;
the persistent-context SHA-256 was
`64e3f879e515b3f47f7b52115ac96c3803bef77b9f07708707de0e27e54801af`.
The recursive fixture inventory independently reproduced 110 files under
`movies/Phase4` and 147 files in the broader movie tree. Provisioning copied
only the 1,362 centrally declared inputs and `tools/build_identity.py --verify`
recomputed all 327 staged pristine pins.

The current DuckStation fork remained at revision
`fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`, with 95 dirty paths. The exact
release binary was SHA-256
`91cbe22b2c2e22ad83d695988ada36bbabb22c65366cb5ec9e8e30784de93af6`.
The regenerated RPC manifest contains 207 methods; its JSON and Markdown
SHA-256 values are `3766b936e3ab92a6e9213b19a2697510440f2f9e75eb72d14322c6eab3115446`
and `d96d50e18bb30f9b5315290666cb38d26c3224e7e5c0fcb317d726e4fd9f8e97`.

## Capsule-first observation

The preservation/freshness validator was run before any live replay:

```text
python3 tools/phase4_trace_capsules.py --movie-root ~/Downloads/ABL/movies/Phase4 --capsule-root ~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v2 --comparison-root ~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v1 --require-byte-identical-comparison --binary-snapshot ~/Downloads/ABL-external-evidence/duckstation-binaries/duckstation-qt-trace-capsule-v1-20260718 --offline-reader-snapshot ~/Downloads/ABL-external-evidence/duckstation-tools/trace_capsule_query-v1-20260718.py --check
PASS: 50/50 capsules, 2442984379 external bytes
```

The exact offline reader SHA-256 was
`b3898f928800efad5a949d1369aa65d786067505e0ed915eec8fdb99f0aa1dde`.
The `E10__hazard_pit_LEVEL02` capsule was complete and nontruncated for all 359
records. An offline RAM change query over the safe-anchor tuple at `0x800A6550`
found change points at movie frames 157 and 249; an execution-hotspot query
bounded the first transition to frames 140..160.

Observation: the capsule supplies frame-boundary registers, RAM, VRAM, SPU and
block-flow evidence, but not the exact instruction writer, short-lived
intermediate value, source-record counterfactual, full-capacity allocator call,
GPU/SPU caller, or source-current binary provenance needed by the stale
artifacts. The Thud recording and the scene-14 strict-pristine save are also not
members of the retained 50-capsule set.

Inference: another capsule replay could not answer the named missing temporal
and causal domains. Fresh isolated API runs were justified for exact writer,
allocator, GPU/SPU and behavioral-control evidence, and for source-current
freshness. No capsule was treated as every-cycle evidence or campaign closure.

## Live escalation and reproduced controls

Every run used a newly created absolute `/tmp` config directory, a unique
loopback port/token, the SHA-1-pinned operator-root pristine CUE/BIN, pre-load
save inspection where applicable, and exact owned-PID cleanup. The operator-root
BIN/CUE SHA-1 values recomputed as `0bc1a29748d4bd608d076495d085e825574880d1`
and `25adb139e50ba28c2d9c1ecab4528e9cf004b1d5` before reuse. No save, movie,
capture, BIOS or disc bytes were added to Git.

The source/fixture freshness chain was replayed in dependency order:

- E06 contact pool, C16 Riverbed Flight and C15 checkpoint/respawn;
- the Thud root followed by arena, completion and reward-volley derivatives;
- the C16 Thud-boulder join, C15 static writer catalog, E08 hazard outcomes,
  C16 death breadth and their downstream joins.

C15 again bound three pit writers and Bug Bar continuous safe-anchor
consumption. E08 again produced health/lives changes in all eight hazard leads.
C16 breadth again joined five natural death paths. Thud again bound the
action-20 source, sound request, SPU control, billboard, grain effect, arena
row, counter-8 completion request and reward volleys.

## Current-toolchain pause-boundary divergence

The first current-binary Thud run stopped on a strict endpoint predicate even
though both causal outcomes matched. A second fresh run reproduced the same
values, separating a tool-boundary change from gameplay divergence. Subsequent
strict guards exposed the complete current endpoint map:

- countdown-zero minus control is `-1` cycle at the same PC `0x8004FEA4`;
- the exact sound-call NOP ends `+1` cycle at the same PC `0x800104B8`;
- visual suppression ends at equal cycle, with natural PC `0x800104B8` and
  suppressed PC `0x80010508`;
- radius control and mutation end at equal cycle and PC `0x80010508`;
- arena threshold control and threshold-zero end at equal cycle and PC
  `0x8004FEA4`.

The guards were updated to these exact values, not widened to accept multiple
outcomes. Frame, SP, causal RAM differences, contact classification, SPU event
counts, framebuffer/object-pick predicates, grain/state writers, health
outcomes and pristine code identities remained exact. The final complete root
replay passed its own low-level evidence audit before retention.

## Reproduced cold-boot divergence

The source-refreshed C15 authored-row provenance replay is the sole remaining
Phase 4 artifact mismatch. Two fresh runs used the centrally pinned from-boot
`movies/go_to_end/LEVEL02.movie.json` (SHA-256
`09daafa2f94a2252e805dea1096e82458bca6864863092b2269ffe57b6dcc502`).
Both retained movie reproducibility and `truncated=false`, but the current
binary remained in scene 0 at both movie frames 6300 and 7000. Consequently the
DAT base/type pointers were correctly zero; the generator refused to retain a
false scene-3 source join. The offline staged census still found the unique
type-1/count-18 record at `REBUILD/files/LEVEL03/LEVEL.DAT` offset `0x458`.

The prior artifact remains valid historical evidence for binary
`c668bf0974a7da5dabdbc4f1bd5311df3027e8af56faceb19ac7648f6f24ccec`,
where frame 7000 reached scene 3, but it is source-stale against the refreshed
C15 artifact. A current-binary timing-matched cold-boot recording or an
autonomously derived deterministic replacement is still required. This is an
open autonomous investigation, not an operator-only blocker.

## Implementation iteration 2 — autonomous C15 repair

Iteration 2 started with the retained capsule lane again. The 50/50 freshness
validator passed for 2,442,984,379 external bytes. The exact pinned offline
reader, SHA-256 `b3898f928800efad5a949d1369aa65d786067505e0ed915eec8fdb99f0aa1dde`,
confirmed that `E10__hazard_pit_LEVEL02` is complete and nontruncated. Safe
anchor RAM at `0x800A6550` changes at movie frames 157 and 249; the 140..160
hotspot window contains resident `0x8004FEA4` and the bounded overlay PCs. The
capsule is save-anchored frame evidence and cannot supply current-binary
cold-boot progression, memory-card provenance, the exact live DAT source join,
or the required unedited behavioral control. That named missing domain
justified the isolated API replay; no capsule result was treated as every-cycle
evidence.

The earlier scene-3 replay was not independent of its profile. Its supposedly
fresh config retained a 131,072-byte card containing completed-game
`BASCUS-94288LEV15:00` and `:01` records. The card SHA-256 is
`63c08f0143e7b714309de900905f22944ae07f1da881ce9aa3a0237a5dacf517`;
a newly created config has no card until the game writes one. The undeclared
completed card is therefore excluded as authority.

An autonomous game-native progression recipe replaces it. The centrally
declared pristine `level01_end_of_stage.sav`, SHA-256
`42047329754c56f6daaf413e192ba8e88ca40889714bbc9f57216f3462ed739f`,
was inspected before load against mounted pristine media. Holding Up for 1500
frames completes LEVEL01; Cross and three Square presses separated by
400/1200/1000/1000-frame waits create exactly one
`BASCUS-94288LEV02:00` record. The isolated transient card is 131,072 bytes,
SHA-256 `5ca4ee4e23d76fe4eb596d0fe7766c481dcac456557756734f28c903fa242d4c`.
The preparation PID is stopped before a second DuckStation process cold-boots
with that same controlled config/card. Card bytes remain under `/tmp` and are
not retained.

With that card, the unedited pinned LEVEL02 movie is reproducible and
nontruncated but its stale Left burst at frames 6307..6315 moves the menu from
Tunnels back to Ant Hill; the control reaches scene 1. Removing only Left from
those nine in-memory frames, without saving a derivative, gives semantic movie
SHA-256 `8ad070c7d00135e6f48956819a8b73669203691145139edb1db5f4c635389e47`.
The branch equals the control through frame 6300, then reaches scene 3 at frame
7600. DAT base `0x8015E22C`, slot-1 pointer `0x8015E684`, the complete
type-0x01 record and selected row 6 again match the unique pinned
`LEVEL03/LEVEL.DAT` bytes. The card is byte-identical before and after both
movie branches.

The final row-provenance artifact is SHA-256
`1da77a6fb0d98775c1671f5384d0e3a9cc875e47069029bbbd2387704abfe592`.
The dedicated two-process declarative scenario is
`tools/scenarios/duckstation/pristine_c15_authored_row_provenance.yaml`,
SHA-256 `81dc60f669be9dfac82f34d9816401398e58d720de0a308a62d064db26a1da9f`.
Its exact current-binary checkpoint dependency is
`1353bd90217a726c432644b2150c15b0ead3bd3d8c07e8840966fc5d7f07f226`;
the refreshed static writer catalog is SHA-256
`6be7a774080c5ed8fb02bce0b50e2cef136924f0b5649b2b0871e8ab068d2aaf`.
Adding the state and movie as explicit central consumers changed the fixture-
manifest identity, so every affected live dependency was replayed from
pristine media instead of having its hash edited in place. E08 hazard outcomes,
C16 breadth, Riverbed Flight, Thud arena/completion/volley and the Thud-boulder
join reproduced their prior bounded conclusions on the current binary. Every
preparation and target process stopped only the PID owned by its isolated
config.

The recomputed Phase-4 inventory now has 42/42 generators and zero stale source
dependencies. This resolves the implementation-iteration-1 C15 freshness gap;
it does not close C15 or Phase 4. Activation/denial policy, indirect/additional
variants, lifecycle breadth and 91 baseline rows remain open. Phase 3's
current-toolchain prerequisite also remains open.

## Machine result and validation

At the implementation-iteration-1 handoff, the method manifest, API index,
retained artifacts, artifact-hash assertions,
tests, campaign inventory, fixture audit and gate were regenerated in machine
order before that prose. `phase4_inventory.py` reported 107 rows, 12
families and 42/42 generators with exactly one source mismatch: the C15
row-provenance artifact above. Knowledge assertions for every completed
finding and completed child campaign are clean. The score remains 16/107
complete and 91 open; prose does not promote any additional row.

Focused changed-artifact validation passed 73 tests, followed by five C16
breadth tests. The full safe suite before the refresh reported 602 passed, 18
failed and 50 deselected; those failures were the stale-artifact and Phase 3
current-toolchain guards that drove this work. A final full safe and clean
checkout result is recorded in the commit handoff after the machine layers and
notes are final.

## Remaining

- Refresh the Phase 3 live evidence declarations against the current 207-method
  debugger binary; its gate must remain open until that exact replay set passes.
- Continue C15 with authored-row activation/denial policy, indirect/additional
  overlay variants and save/load/scene-transition breadth.
- Continue the 91 acceptance rows still open under the binding Phase 4 roadmap.
