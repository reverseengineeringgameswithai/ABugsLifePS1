---
kind: experiment
id: EXP_2026-07-26_phase4_fmv_menu_phase_neutral_preflight
date: 2026-07-26
phase: 4
campaign: fmv_playback
row: E15_fmv
status: planned
confidence: high
source_state: original_game
---

# Phase 4 FMV Menu phase-neutral observer preflight

## Work packet

- Campaign and rows: `fmv_playback`; only `E15_fmv`.
- First unmet nine-dimension predicate: `lifecycle`.
- Exact claim: for each central Menu movie, one debugger-native,
  phase-neutral nine-PC observer hits all three boot callers and none of the
  six non-boot callers through the complete from-boot input span.
- Falsifier: any non-boot hit, missed boot caller, native endpoint inequality,
  failure to reset the recorded anchor reproducibly, truncation, incomplete
  input span, or failed receipt/prelude identity join.
- Needed evidence domain: original interface execution coverage plus the
  native cached-interpreter control.
- Predicted authoritative machine layer: the typed direct
  `movie.traceToFrame` command/result retained by
  `tools/phase4_fmv_menu_phase_neutral_live.py`; this can exclude a bounded
  natural lead but cannot by itself promote the lifecycle dimension.

## Ordered evidence

The required capsule set, offline opportunity queue, derived-index catalog and
closure-debt ledger were regenerated in order. They report 55 valid capsules,
107 rows with `offline_ready=0`, nine reusable indexes over 34 rows, and only
`fmv_playback` selected. E15 remains four dimensions met and five remaining.

Before selection, the recursive operator inventory counted 110 files
(153,880,509 bytes) under `movies/Phase4`, 147 files (420,121,736 bytes) under
the broader operator movie tree, and 135 centrally provisioned files
(395,715,280 bytes) under this worktree's `movies` tree. The two Menu
recordings were already centrally declared; no recording was requested,
copied, or committed.

The retained `fmv-lifecycle-v2` index was queried before any capsule-byte scan.
The closed `abl-phase4-offline-query/1` receipt is:

```text
receipt:
  5820a478e6c3605cc1b563815a33d88b84593f7e1abab743282b840ad97324c6
input index:
  e232f9cd3da57de3f794495b0789904c6cb36bd8152e67f3f7d12576d5c828ab
output:
  7d280901605fc468072fae5cc9c1125060307a9c6a0ee55231aaf153231703c5
preservation:
  42a0d2923c4d56e7416eb9d1ed6ca640c9206af38db2646b5d5cd5c180ead5c5
execution:
  exit 0; stdout "PASS: offline query"
```

Both exact Menu hashes return count zero with no truncation. Static
reconstruction still closes the search to 47 selectors, 40 manifest cases and
exactly nine direct callers. Thus the missing domain is natural execution
coverage for these two declared movie identities, not another offline
correlation or another static xref.

Two additional current-run receipts independently parse every centrally
provisioned movie frame and preserve the faithful input bounds:

```text
Menu-Navigation.movie.json:
  receipt 2d069dd315191d2f624bdd27c0a7c75cc58c146083a4c3b8b1ca61fecb9de743
  output  4d861ee2d3d25965de4c4d7a449b07230526fce27a73b46870daf2c0f3ea4e17
  frames  0..7792 (7,793 samples)
Menu-Navigation.movie_v2.json:
  receipt cb9554940b9b1b7a74c7b8ff4b6010c17fd72070a302669b83ffbd4c448f9528
  output  80b424108479c8e904f9aac6644a630e325f95bade7dc1a764482b4822949f29
  frames  0..7361 (7,362 samples)
```

## Method change and live boundary

The prior split execTrace plan is rejected evidence:
[[EXP_2026-07-26_phase4_fmv_menu_owner_control_falsified]]. Its plausible
three-positive/six-zero counts cannot support an exclusion because the two
instrumented endpoints diverged.

The replacement makes the observer one direct native operation covering nine
singleton PCs. `movie.traceToFrame` resets the recorded movie anchor for an
uninstrumented pass and a passive cached-interpreter pass, then derives
`cycle_neutral` from exact RAM, register, cycle, frame and playback-index
equality. A two-job uninstrumented `scenario.runBatch` remains in the same
owned server-session command stream, and each precise receipt names a
separately retained passive prelude with a strictly wider window.

The receipt validator previously closed command events to identities and
scenario batch methods. It now admits only the typed
`movie.traceToFrame` parameter/result schema, recomputes every coverage total,
derives all five native comparisons from the retained endpoints, joins the
command to the typed observer plan, and requires it to follow the completed
atomic control. A complete non-neutral or non-boot result remains a closed
falsification receipt and cannot support ownership; truncation or incomplete
results are rejected. Tests mutate the nine-PC set, instrumentation boundary,
target frame, native comparison, truncation and non-boot counts.

## Why DuckStation did not launch

The controller's immutable iteration-1 before-ledger, SHA-256
`8f05385efcb469a72428a97c4279f76a2bcc2b31b7f8e64da8648b026e21460f`,
contains 17 executed entries and zero planned entries. An investigator receipt
must join a unique planned escalation in that before-ledger. Retrospectively
adding one and launching in the same iteration would make every receipt
inadmissible.

Therefore no emulator process was launched and no live receipt was authored.
The generated after-ledger now predeclares
`P4-ITER94-E15-MENU-PHASE-NEUTRAL-OWNER-COVERAGE` with four receipt identities
and the exact live method. The next controller iteration may execute it from
four fresh isolated profiles. Until then, no original-game behavior, Canon
fact, MOD-private state, row, or closure dimension is promoted.
